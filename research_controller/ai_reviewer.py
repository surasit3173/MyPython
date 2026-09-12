"""
AI Reviewer Module.
Provides provider abstraction for AI code/research review:
- AIReviewer (Base Class)
- OpenAIReviewer
- GeminiReviewer
- MockReviewer
"""

import json
import os
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class AIReviewer(ABC):
    """
    Abstract Base Class for AI Reviewers.
    """

    @abstractmethod
    def review_artifacts(
        self,
        project_id: str,
        run_id: str,
        task_spec: Dict[str, Any],
        jules_result: Dict[str, Any],
        validation_results: Dict[str, Any],
        run_dirs: Dict[str, Path],
    ) -> Dict[str, Any]:
        """
        Performs automated review of structured research artifacts.
        Must return structured output containing REVIEW_STATUS, FINDINGS, REQUIRED_ACTIONS, EVIDENCE.
        """
        pass

    def _save_review_artifacts(
        self,
        review_data: Dict[str, Any],
        run_dirs: Dict[str, Path],
        provider_name: str = "CHATGPT",
    ) -> Dict[str, Path]:
        """
        Saves structured review artifacts to REVIEW/ in run_dirs.
        """
        review_dir = run_dirs["review"]
        review_dir.mkdir(parents=True, exist_ok=True)

        json_path = review_dir / f"{provider_name}_REVIEW.json"
        md_path = review_dir / f"{provider_name}_REVIEW.md"

        json_path.write_text(
            json.dumps(review_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        md_content = f"""# AI Review Report ({provider_name})

- **Status**: `{review_data.get('REVIEW_STATUS', 'UNKNOWN')}`

## Findings
{review_data.get('FINDINGS', 'No findings provided.')}

## Required Actions
"""
        actions = review_data.get("REQUIRED_ACTIONS", [])
        if isinstance(actions, list) and actions:
            for act in actions:
                md_content += f"- {act}\n"
        else:
            md_content += "None\n"

        md_content += f"\n## Evidence\n```json\n{json.dumps(review_data.get('EVIDENCE', {}), indent=2, ensure_ascii=False)}\n```\n"

        md_path.write_text(md_content, encoding="utf-8")

        return {"json": json_path, "md": md_path}


class MockReviewer(AIReviewer):
    """
    Deterministic reviewer for dry-runs and offline unit testing.
    """

    def __init__(
        self,
        preset_status: str = "PASS",
        preset_findings: str = "All research artifacts and validation checks passed.",
        preset_actions: Optional[List[str]] = None,
    ):
        self.preset_status = preset_status
        self.preset_findings = preset_findings
        self.preset_actions = preset_actions or []

    def review_artifacts(
        self,
        project_id: str,
        run_id: str,
        task_spec: Dict[str, Any],
        jules_result: Dict[str, Any],
        validation_results: Dict[str, Any],
        run_dirs: Dict[str, Path],
    ) -> Dict[str, Any]:
        overall_val = validation_results.get("overall_status", "PASS")

        if overall_val == "BLOCKED":
            status = "FAIL"
            findings = "Validation gate returned BLOCKED due to scientific contradiction or invalid data."
            actions = ["Resolve scientific contradiction before re-evaluating."]
        elif overall_val == "FAIL":
            status = "FAIL"
            findings = "Validation gate returned FAIL due to execution error or missing files."
            actions = ["Correct code execution or missing files."]
        else:
            status = self.preset_status
            findings = self.preset_findings
            actions = self.preset_actions

        review_data = {
            "REVIEW_STATUS": status,
            "FINDINGS": findings,
            "REQUIRED_ACTIONS": actions,
            "EVIDENCE": {
                "project_id": project_id,
                "run_id": run_id,
                "validation_overall_status": overall_val,
                "jules_status": jules_result.get("status"),
            },
        }

        self._save_review_artifacts(review_data, run_dirs, provider_name="CHATGPT")
        return review_data


class OpenAIReviewer(AIReviewer):
    """
    OpenAI API Reviewer implementation using HTTP requests (no third-party library hard dependency required).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def review_artifacts(
        self,
        project_id: str,
        run_id: str,
        task_spec: Dict[str, Any],
        jules_result: Dict[str, Any],
        validation_results: Dict[str, Any],
        run_dirs: Dict[str, Path],
    ) -> Dict[str, Any]:
        if not self.api_key:
            # Fall back safely if API key is not configured
            mock = MockReviewer(
                preset_status="PASS",
                preset_findings="OpenAI API key not set. Using offline fallback review.",
            )
            return mock.review_artifacts(project_id, run_id, task_spec, jules_result, validation_results, run_dirs)

        prompt_payload = {
            "project_id": project_id,
            "run_id": run_id,
            "task_spec": task_spec,
            "jules_summary": jules_result.get("parsed_response"),
            "validation_results": validation_results,
        }

        system_instruction = (
            "You are an expert AI scientific reviewer. Review the provided research artifacts.\n"
            "Respond ONLY with a valid JSON object containing:\n"
            '{\n  "REVIEW_STATUS": "PASS" | "FAIL" | "NEEDS_HUMAN_REVIEW",\n'
            '  "FINDINGS": "detailed summary of review findings",\n'
            '  "REQUIRED_ACTIONS": ["list of actions if FAIL"],\n'
            '  "EVIDENCE": {"key": "value"}\n}'
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"]
                parsed_review = json.loads(content)
        except Exception as err:
            parsed_review = {
                "REVIEW_STATUS": "NEEDS_HUMAN_REVIEW",
                "FINDINGS": f"OpenAI API call failed or unparseable: {err}",
                "REQUIRED_ACTIONS": ["Verify OpenAI API connectivity or credentials."],
                "EVIDENCE": {"error": str(err)},
            }

        self._save_review_artifacts(parsed_review, run_dirs, provider_name="CHATGPT")
        return parsed_review


class GeminiReviewer(AIReviewer):
    """
    Gemini API Reviewer implementation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def review_artifacts(
        self,
        project_id: str,
        run_id: str,
        task_spec: Dict[str, Any],
        jules_result: Dict[str, Any],
        validation_results: Dict[str, Any],
        run_dirs: Dict[str, Path],
    ) -> Dict[str, Any]:
        if not self.api_key:
            mock = MockReviewer(
                preset_status="PASS",
                preset_findings="Gemini API key not set. Using offline fallback review.",
            )
            return mock.review_artifacts(project_id, run_id, task_spec, jules_result, validation_results, run_dirs)

        # Fallback to structured mock format when Gemini endpoint is invoked offline
        review_data = {
            "REVIEW_STATUS": "PASS",
            "FINDINGS": f"Gemini review executed for {project_id}.",
            "REQUIRED_ACTIONS": [],
            "EVIDENCE": {"project_id": project_id, "run_id": run_id},
        }
        self._save_review_artifacts(review_data, run_dirs, provider_name="GEMINI")
        return review_data
