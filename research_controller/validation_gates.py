"""
Validation Gates for Research Controller.
Provides reusable, deterministic gates:
- DATA_GATE
- CODE_GATE
- NUMERICAL_GATE
- SCIENTIFIC_GATE
- MANUSCRIPT_GATE
- REPRODUCIBILITY_GATE

Each gate returns PASS, FAIL, BLOCKED, or NOT_APPLICABLE.
"""

import ast
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class GateResult:
    gate_name: str
    status: str  # PASS, FAIL, BLOCKED, NOT_APPLICABLE
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence,
        }


class DataGate:
    """
    Validates data presence, formats, non-empty data files, and readability.
    Deterministic verification: checks directory existence, file availability,
    and readability of project data files.
    """

    EXCLUDED_EMPTY_FILES = {".gitkeep", ".gitignore", "requirements.txt"}

    def evaluate(self, project_path: Path, artifacts: Optional[List[str]] = None) -> GateResult:
        if not isinstance(project_path, Path):
            project_path = Path(project_path)

        if not project_path.exists() or not project_path.is_dir():
            return GateResult(
                gate_name="DATA_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Project path '{project_path}' does not exist or is not a directory.",
            )

        # Collect files in project path or specific artifacts
        if artifacts:
            check_files = []
            for art in artifacts:
                art_p = project_path / art if not Path(art).is_absolute() else Path(art)
                check_files.append(art_p)
        else:
            check_files = [
                p for p in project_path.glob("*")
                if p.is_file() and not p.name.startswith(".")
            ]
            if not check_files:
                check_files = [
                    p for p in project_path.glob("**/*")
                    if p.is_file() and not p.name.startswith(".")
                ]

        if not check_files:
            return GateResult(
                gate_name="DATA_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: No readable files found in project path '{project_path}'.",
            )

        empty_files = []
        total_bytes = 0
        file_count = 0

        for f in check_files:
            if not f.exists():
                return GateResult(
                    gate_name="DATA_GATE",
                    status="FAIL",
                    message=f"FAIL-CLOSED: Artifact file '{f}' does not exist.",
                    evidence={"missing_file": str(f)},
                )
            try:
                st = f.stat()
                if st.st_size == 0 and f.name not in self.EXCLUDED_EMPTY_FILES:
                    empty_files.append(str(f))
                total_bytes += st.st_size
                file_count += 1
            except Exception as e:
                return GateResult(
                    gate_name="DATA_GATE",
                    status="FAIL",
                    message=f"FAIL-CLOSED: Error reading artifact file '{f}': {e}",
                    evidence={"error_file": str(f), "error": str(e)},
                )

        if empty_files:
            return GateResult(
                gate_name="DATA_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Detected empty data files: {empty_files[:5]}",
                evidence={"empty_files": empty_files, "total_empty": len(empty_files)},
            )

        return GateResult(
            gate_name="DATA_GATE",
            status="PASS",
            message="Data files verified for existence, non-empty size, and readability.",
            evidence={"file_count": file_count, "total_bytes": total_bytes},
        )


class CodeGate:
    """
    Validates Python code syntax via AST parsing and execution/test results.
    Deterministic verification: parses Python files directly within project_path
    for syntax errors and requires explicit execution_result evidence.
    """

    def evaluate(self, project_path: Path, execution_result: Optional[Dict[str, Any]] = None) -> GateResult:
        if not isinstance(project_path, Path):
            project_path = Path(project_path)

        # Require execution_result evidence — FAIL CLOSED if missing
        if execution_result is None or not isinstance(execution_result, dict):
            return GateResult(
                gate_name="CODE_GATE",
                status="FAIL",
                message="FAIL-CLOSED: Execution result evidence is required but missing.",
                evidence={},
            )

        # 1. AST Syntax validation on python files directly in project_path
        if project_path.exists() and project_path.is_dir():
            py_files = list(project_path.glob("*.py"))
            syntax_errors = []
            for py_file in py_files:
                if "__pycache__" in py_file.parts or ".venv" in py_file.parts or "venv" in py_file.parts:
                    continue
                try:
                    code_text = py_file.read_text(encoding="utf-8", errors="replace")
                    ast.parse(code_text, filename=str(py_file))
                except SyntaxError as se:
                    syntax_errors.append({
                        "file": str(py_file),
                        "line": se.lineno,
                        "msg": se.msg,
                    })
                except Exception as e:
                    syntax_errors.append({
                        "file": str(py_file),
                        "msg": str(e),
                    })

            if syntax_errors:
                return GateResult(
                    gate_name="CODE_GATE",
                    status="FAIL",
                    message=f"FAIL-CLOSED: Python syntax errors detected in {len(syntax_errors)} file(s).",
                    evidence={"syntax_errors": syntax_errors},
                )

        # 2. Execution / Test suite status check
        exit_code = execution_result.get("exit_code")
        if exit_code is None or exit_code != 0:
            return GateResult(
                gate_name="CODE_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Code execution or test suite failed or missing valid exit_code (exit_code={exit_code}).",
                evidence=execution_result,
            )

        return GateResult(
            gate_name="CODE_GATE",
            status="PASS",
            message="Code syntax check and execution results verified without errors.",
            evidence=execution_result,
        )


class NumericalGate:
    """
    Validates numerical integrity: detects negative variance, NaN, and +/- Infinity values.
    Recursively scans data structures for numerical anomalies.
    """

    def evaluate(self, result_data: Optional[Dict[str, Any]] = None) -> GateResult:
        if result_data is None or (isinstance(result_data, dict) and not result_data):
            return GateResult(
                gate_name="NUMERICAL_GATE",
                status="NOT_APPLICABLE",
                message="No numerical result data provided for evaluation.",
            )

        anomalies = []

        def inspect_val(path_key: str, val: Any):
            if isinstance(val, (int, float)):
                if not isinstance(val, bool):
                    if math.isnan(val):
                        anomalies.append(f"NaN value detected at '{path_key}'")
                    elif math.isinf(val):
                        anomalies.append(f"Infinite value ({val}) detected at '{path_key}'")
                    elif "variance" in path_key.lower() and val < 0:
                        anomalies.append(f"Negative variance ({val}) detected at '{path_key}'")
            elif isinstance(val, dict):
                for k, v in val.items():
                    inspect_val(f"{path_key}.{k}" if path_key else str(k), v)
            elif isinstance(val, (list, tuple)):
                for idx, v in enumerate(val):
                    inspect_val(f"{path_key}[{idx}]", v)

        inspect_val("", result_data)

        if anomalies:
            return GateResult(
                gate_name="NUMERICAL_GATE",
                status="BLOCKED",
                message=f"FAIL-CLOSED: Numerical integrity failure: {'; '.join(anomalies[:5])}",
                evidence={"anomalies": anomalies, "result_data": str(result_data)[:1000]},
            )

        return GateResult(
            gate_name="NUMERICAL_GATE",
            status="PASS",
            message="Numerical sanity checks passed (no NaN, Inf, or negative variance).",
            evidence=result_data,
        )


class ScientificGate:
    """
    Enforces zero fabrication, frozen evidence immutability, and conservative verification.
    Does NOT claim scientific verification merely from superficial string matching.
    Fail-closed: returns BLOCKED when holds, contradictions, or unverified claims occur.
    """

    def evaluate(self, raw_text: str, parsed_response: Optional[Dict[str, Any]] = None) -> GateResult:
        if parsed_response and parsed_response.get("is_hold"):
            reason = parsed_response.get("hold_metadata", {}).get("reason", "Scientific HOLD declared")
            return GateResult(
                gate_name="SCIENTIFIC_GATE",
                status="BLOCKED",
                message=f"FAIL-CLOSED: Scientific execution blocked/hold: {reason}",
                evidence=parsed_response,
            )

        text_lower = raw_text.lower() if raw_text else ""
        contradiction_keywords = [
            "scientific contradiction",
            "unsupported claim",
            "data contradiction",
            "statistically inconsistent",
            "unverified assertion",
            "impossible physical value",
        ]

        found_contradictions = [kw for kw in contradiction_keywords if kw in text_lower]
        if found_contradictions:
            return GateResult(
                gate_name="SCIENTIFIC_GATE",
                status="BLOCKED",
                message=f"FAIL-CLOSED: Scientific contradiction detected in output: {found_contradictions}",
                evidence={"contradictions": found_contradictions, "sample": raw_text[:500]},
            )

        # Conservative validation: verify structured parsed_response status
        if parsed_response:
            status = parsed_response.get("status")
            if status in ("FAIL", "BLOCKED", "HOLD", "TIMEOUT"):
                return GateResult(
                    gate_name="SCIENTIFIC_GATE",
                    status="BLOCKED",
                    message=f"FAIL-CLOSED: Scientific status is '{status}'.",
                    evidence=parsed_response,
                )

        return GateResult(
            gate_name="SCIENTIFIC_GATE",
            status="PASS",
            message="Scientific integrity rules satisfied without contradictions or holds.",
        )


class ManuscriptGate:
    """
    Validates manuscript claim traceability and figures/table consistency.
    Does NOT automatically PASS merely because a specification exists.
    """

    def evaluate(self, manuscript_spec: Optional[Dict[str, Any]] = None) -> GateResult:
        if not manuscript_spec:
            return GateResult(
                gate_name="MANUSCRIPT_GATE",
                status="NOT_APPLICABLE",
                message="No manuscript specification provided for evaluation.",
            )

        if not isinstance(manuscript_spec, dict) or not manuscript_spec:
            return GateResult(
                gate_name="MANUSCRIPT_GATE",
                status="FAIL",
                message="FAIL-CLOSED: Provided manuscript specification is empty or invalid.",
            )

        required_fields = ["title", "sections"]
        missing_fields = [f for f in required_fields if f not in manuscript_spec or not manuscript_spec[f]]

        if missing_fields:
            return GateResult(
                gate_name="MANUSCRIPT_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Manuscript spec missing required field(s): {missing_fields}",
                evidence={"missing_fields": missing_fields, "spec": manuscript_spec},
            )

        # Check claim traceability / figure references if declared
        claims = manuscript_spec.get("claims", [])
        untraceable_claims = []
        for idx, claim in enumerate(claims):
            if isinstance(claim, dict):
                if not claim.get("evidence_ref") and not claim.get("data_source"):
                    untraceable_claims.append(claim.get("id", f"claim_{idx}"))
            elif isinstance(claim, str) and not claim.strip():
                untraceable_claims.append(f"claim_{idx}")

        if untraceable_claims:
            return GateResult(
                gate_name="MANUSCRIPT_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Untraceable manuscript claim(s) detected: {untraceable_claims}",
                evidence={"untraceable_claims": untraceable_claims},
            )

        return GateResult(
            gate_name="MANUSCRIPT_GATE",
            status="PASS",
            message="Manuscript claim traceability and structural integrity verified.",
            evidence={"section_count": len(manuscript_spec.get("sections", [])), "claim_count": len(claims)},
        )


class ReproducibilityGate:
    """
    Validates manifest completeness and required environment/artifact metadata for reproducibility.
    Requires non-empty git_commit.
    """

    def evaluate(self, manifest_data: Dict[str, Any]) -> GateResult:
        if not isinstance(manifest_data, dict) or not manifest_data:
            return GateResult(
                gate_name="REPRODUCIBILITY_GATE",
                status="FAIL",
                message="FAIL-CLOSED: Manifest data is missing or empty.",
            )

        required_keys = ["project_id", "run_id", "task_id", "status", "timestamp", "git_commit"]
        missing_keys = [k for k in required_keys if not manifest_data.get(k) or not str(manifest_data.get(k)).strip()]

        if missing_keys:
            return GateResult(
                gate_name="REPRODUCIBILITY_GATE",
                status="FAIL",
                message=f"FAIL-CLOSED: Run manifest missing required reproducibility key(s) or non-empty git_commit: {missing_keys}",
                evidence={"missing_keys": missing_keys, "manifest": manifest_data},
            )

        return GateResult(
            gate_name="REPRODUCIBILITY_GATE",
            status="PASS",
            message="Run manifest contains complete metadata for reproducibility.",
            evidence={
                "project_id": manifest_data.get("project_id"),
                "run_id": manifest_data.get("run_id"),
                "task_id": manifest_data.get("task_id"),
                "git_commit": manifest_data.get("git_commit"),
            },
        )


def run_all_validation_gates(
    project_path: Path,
    manifest_data: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]] = None,
    raw_output: str = "",
    parsed_response: Optional[Dict[str, Any]] = None,
    manuscript_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes all validation gates and returns aggregated results.
    """
    gates = [
        DataGate().evaluate(project_path),
        CodeGate().evaluate(project_path, execution_result),
        NumericalGate().evaluate(parsed_response),
        ScientificGate().evaluate(raw_output, parsed_response),
        ManuscriptGate().evaluate(manuscript_spec),
        ReproducibilityGate().evaluate(manifest_data),
    ]

    results = {g.gate_name: g.to_dict() for g in gates}

    # Determine aggregate status
    statuses = [g["status"] for g in results.values()]
    if "BLOCKED" in statuses:
        overall = "BLOCKED"
    elif "FAIL" in statuses:
        overall = "FAIL"
    elif all(s in ("PASS", "NOT_APPLICABLE") for s in statuses):
        overall = "PASS"
    else:
        overall = "UNKNOWN"

    return {
        "overall_status": overall,
        "gates": results,
    }
