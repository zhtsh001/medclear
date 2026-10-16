from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
POLICY_JSON_PATH = ROOT_DIR / "Policy_Extraction" / "IIT_vaccine_policy.json"
SAMPLE_INITIAL_RESULT_PATH = ROOT_DIR / "IIT_Record4_Result.json"
SAMPLE_FINAL_RESULT_PATH = ROOT_DIR / "IIT_Record4_Final_Audit.json"
FORCE_SAMPLE_ENV = "MEDCLEAR_DEMO_FORCE_SAMPLE"


def _relative_path(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)


def _force_sample_mode() -> bool:
    value = os.getenv(FORCE_SAMPLE_ENV, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _fallback_result(sample_path: Path, output_path: Path) -> dict[str, Any]:
    raise RuntimeError(
        "The audit could not complete. No sample medical reports are bundled in this public source. "
        "Check GEMINI_API_KEY and provider access; do not substitute another person's audit result."
    )


def load_result_json(relative_path: str | None) -> dict[str, Any] | None:
    if not relative_path:
        return None

    result_path = ROOT_DIR / relative_path
    if not result_path.exists():
        return None

    return _load_json(result_path)


def run_initial_audit(record_id: int, student_age: int) -> dict[str, Any]:
    pdf_path = ROOT_DIR / "Immunization_Records" / f"Record{record_id}.pdf"
    output_path = ROOT_DIR / f"IIT_Record{record_id}_Result.json"

    if not pdf_path.exists():
        raise FileNotFoundError(f"Initial PDF not found: {pdf_path}")

    if _force_sample_mode():
        result = _fallback_result(SAMPLE_INITIAL_RESULT_PATH, output_path)
        return {
            "result": result,
            "source": "sample_fallback",
            "output_path": _relative_path(output_path),
            "error": "Forced sample mode is enabled.",
        }

    error_message = None

    try:
        from main import audit_student_record

        result = audit_student_record(
            pdf_path=str(pdf_path),
            policy_json_path=str(POLICY_JSON_PATH),
            student_age=student_age,
        )

        if isinstance(result, dict):
            _write_json(output_path, result)
            return {
                "result": result,
                "source": "live",
                "output_path": _relative_path(output_path),
                "error": None,
            }

        error_message = "Initial audit returned no structured result."
    except Exception as exc:
        error_message = str(exc)

    result = _fallback_result(SAMPLE_INITIAL_RESULT_PATH, output_path)
    return {
        "result": result,
        "source": "sample_fallback",
        "output_path": _relative_path(output_path),
        "error": error_message,
    }


def run_final_audit(record_id: int, student_age: int) -> dict[str, Any]:
    original_pdf_path = ROOT_DIR / "Immunization_Records" / f"Record{record_id}.pdf"
    supplement_pdf_path = ROOT_DIR / "Immunization_Records" / f"Supplementary_Materials{record_id}.pdf"
    output_path = ROOT_DIR / f"IIT_Record{record_id}_Final_Audit.json"

    if not original_pdf_path.exists():
        raise FileNotFoundError(f"Initial PDF not found: {original_pdf_path}")

    if not supplement_pdf_path.exists():
        raise FileNotFoundError(f"Supplementary PDF not found: {supplement_pdf_path}")

    if _force_sample_mode():
        result = _fallback_result(SAMPLE_FINAL_RESULT_PATH, output_path)
        return {
            "result": result,
            "source": "sample_fallback",
            "output_path": _relative_path(output_path),
            "error": "Forced sample mode is enabled.",
        }

    error_message = None

    try:
        from re_audit import run_re_audit

        result = run_re_audit(
            original_pdf_path=str(original_pdf_path),
            supplement_pdf_path=str(supplement_pdf_path),
            policy_json_path=str(POLICY_JSON_PATH),
            student_age=student_age,
        )

        if isinstance(result, dict):
            _write_json(output_path, result)
            return {
                "result": result,
                "source": "live",
                "output_path": _relative_path(output_path),
                "error": None,
            }

        error_message = "Final audit returned no structured result."
    except Exception as exc:
        error_message = str(exc)

    result = _fallback_result(SAMPLE_FINAL_RESULT_PATH, output_path)
    return {
        "result": result,
        "source": "sample_fallback",
        "output_path": _relative_path(output_path),
        "error": error_message,
    }
