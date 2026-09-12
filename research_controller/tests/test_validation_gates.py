"""
Unit and regression tests for validation_gates.py
"""

import math
import tempfile
import unittest
from pathlib import Path

from validation_gates import (
    CodeGate,
    DataGate,
    ManuscriptGate,
    NumericalGate,
    ReproducibilityGate,
    ScientificGate,
    run_all_validation_gates,
)


class TestValidationGates(unittest.TestCase):
    def test_data_gate_non_existent_directory(self):
        res = DataGate().evaluate(Path("/non_existent_path_xyz123"))
        self.assertEqual(res.status, "FAIL")
        self.assertIn("does not exist", res.message)

    def test_data_gate_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = DataGate().evaluate(Path(tmpdir))
            self.assertEqual(res.status, "FAIL")
            self.assertIn("No readable files found", res.message)

    def test_data_gate_empty_data_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "empty_data.csv").write_bytes(b"")
            res = DataGate().evaluate(tmp_path)
            self.assertEqual(res.status, "FAIL")
            self.assertIn("Detected empty data files", res.message)

    def test_data_gate_valid_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "valid_data.csv").write_text("header,val\n1,2", encoding="utf-8")
            res = DataGate().evaluate(tmp_path)
            self.assertEqual(res.status, "PASS")

    def test_code_gate_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "invalid_syntax.py").write_text("def broken_func(:", encoding="utf-8")
            res = CodeGate().evaluate(tmp_path)
            self.assertEqual(res.status, "FAIL")
            self.assertIn("Python syntax errors detected", res.message)

    def test_code_gate_execution_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "valid.py").write_text("x = 1", encoding="utf-8")
            res = CodeGate().evaluate(tmp_path, execution_result={"exit_code": 1, "error": "Crash"})
            self.assertEqual(res.status, "FAIL")
            self.assertIn("exit code 1", res.message)

    def test_numerical_gate_negative_variance(self):
        res = NumericalGate().evaluate({"temperature_variance": -0.05})
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("Negative variance", res.message)

    def test_numerical_gate_nan_and_inf(self):
        res_nan = NumericalGate().evaluate({"metric": float("nan")})
        self.assertEqual(res_nan.status, "BLOCKED")
        self.assertIn("NaN value detected", res_nan.message)

        res_inf = NumericalGate().evaluate({"metric": float("inf")})
        self.assertEqual(res_inf.status, "BLOCKED")
        self.assertIn("Infinite value", res_inf.message)

    def test_scientific_gate_holds_and_contradictions(self):
        res_hold = ScientificGate().evaluate("Output ok", {"is_hold": True, "hold_metadata": {"reason": "Data gap"}})
        self.assertEqual(res_hold.status, "BLOCKED")

        res_contra = ScientificGate().evaluate("A scientific contradiction was found in precipitation trends.")
        self.assertEqual(res_contra.status, "BLOCKED")

    def test_manuscript_gate_validation(self):
        # Empty spec -> NOT_APPLICABLE
        res_none = ManuscriptGate().evaluate(None)
        self.assertEqual(res_none.status, "NOT_APPLICABLE")

        # Incomplete spec -> FAIL
        res_inc = ManuscriptGate().evaluate({"title": "Draft"})
        self.assertEqual(res_inc.status, "FAIL")

        # Untraceable claims -> FAIL
        res_untrace = ManuscriptGate().evaluate({
            "title": "Draft",
            "sections": ["Abstract"],
            "claims": [{"id": "c1"}]  # missing evidence_ref / data_source
        })
        self.assertEqual(res_untrace.status, "FAIL")

        # Valid spec -> PASS
        res_valid = ManuscriptGate().evaluate({
            "title": "Valid Draft",
            "sections": ["Abstract", "Methods"],
            "claims": [{"id": "c1", "evidence_ref": "Fig 1"}]
        })
        self.assertEqual(res_valid.status, "PASS")

    def test_reproducibility_gate(self):
        # Missing keys -> FAIL
        res_inc = ReproducibilityGate().evaluate({"project_id": "P1"})
        self.assertEqual(res_inc.status, "FAIL")

        # Complete -> PASS
        res_ok = ReproducibilityGate().evaluate({
            "project_id": "P1",
            "run_id": "R1",
            "task_id": "T1",
            "status": "PASS",
            "timestamp": "2026-09-12T00:00:00Z",
        })
        self.assertEqual(res_ok.status, "PASS")


if __name__ == "__main__":
    unittest.main()
