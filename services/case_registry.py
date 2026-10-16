from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT_DIR / "data" / "demo_cases.json"
IMMUNIZATION_DIR = ROOT_DIR / "Immunization_Records"

STATUS_LABELS = {
    "new": "Waiting for initial upload",
    "initial_uploaded": "Initial PDF uploaded",
    "initial_review_complete": "Initial audit complete",
    "supplement_uploaded": "Supplement uploaded",
    "final_review_complete": "Final audit complete",
}

CASE_FIELDS = {
    "record_id",
    "age",
    "status",
    "created_at",
    "updated_at",
    "initial_pdf_path",
    "supplement_pdf_path",
    "initial_result_path",
    "final_result_path",
    "initial_result_source",
    "final_result_source",
    "initial_error",
    "final_error",
}


def _now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _relative_path(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def _read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"cases": {}}

    with REGISTRY_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    data.setdefault("cases", {})
    return data


def _write_registry(data: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _extract_record_id(name: str, pattern: str) -> int | None:
    match = re.match(pattern, name)
    if not match:
        return None
    return int(match.group(1))


def _known_record_ids() -> set[int]:
    data = _read_registry()
    record_ids = {int(record_id) for record_id in data["cases"].keys()}

    if IMMUNIZATION_DIR.exists():
        for path in IMMUNIZATION_DIR.iterdir():
            if path.is_file():
                record_id = _extract_record_id(path.name, r"Record(\d+)\.pdf")
                if record_id is not None:
                    record_ids.add(record_id)

                record_id = _extract_record_id(path.name, r"Supplementary_Materials(\d+)\.pdf")
                if record_id is not None:
                    record_ids.add(record_id)

    for path in ROOT_DIR.iterdir():
        if not path.is_file():
            continue

        record_id = _extract_record_id(path.name, r"IIT_Record(\d+)_Result\.json")
        if record_id is not None:
            record_ids.add(record_id)

        record_id = _extract_record_id(path.name, r"IIT_Record(\d+)_Final_Audit\.json")
        if record_id is not None:
            record_ids.add(record_id)

    return record_ids


def _default_case(record_id: int) -> dict[str, Any]:
    timestamp = _now_str()
    return {
        "record_id": record_id,
        "age": None,
        "status": "new",
        "created_at": timestamp,
        "updated_at": timestamp,
        "initial_pdf_path": None,
        "supplement_pdf_path": None,
        "initial_result_path": None,
        "final_result_path": None,
        "initial_result_source": None,
        "final_result_source": None,
        "initial_error": None,
        "final_error": None,
    }


def _discover_case_assets(record_id: int) -> dict[str, str]:
    discovered: dict[str, str] = {}

    initial_pdf = IMMUNIZATION_DIR / f"Record{record_id}.pdf"
    supplement_pdf = IMMUNIZATION_DIR / f"Supplementary_Materials{record_id}.pdf"
    initial_result = ROOT_DIR / f"IIT_Record{record_id}_Result.json"
    final_result = ROOT_DIR / f"IIT_Record{record_id}_Final_Audit.json"

    if initial_pdf.exists():
        discovered["initial_pdf_path"] = _relative_path(initial_pdf)
    if supplement_pdf.exists():
        discovered["supplement_pdf_path"] = _relative_path(supplement_pdf)
    if initial_result.exists():
        discovered["initial_result_path"] = _relative_path(initial_result)
    if final_result.exists():
        discovered["final_result_path"] = _relative_path(final_result)

    return discovered


def _infer_status(case: dict[str, Any]) -> str:
    if case.get("final_result_path"):
        return "final_review_complete"
    if case.get("supplement_pdf_path"):
        return "supplement_uploaded"
    if case.get("initial_result_path"):
        return "initial_review_complete"
    if case.get("initial_pdf_path"):
        return "initial_uploaded"
    return "new"


def _sanitize_case(case: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for field in CASE_FIELDS:
        if field in case:
            sanitized[field] = case[field]
    return sanitized


def _decorate_case(case: dict[str, Any]) -> dict[str, Any]:
    decorated = dict(case)
    decorated["status"] = _infer_status(decorated)
    decorated["status_label"] = STATUS_LABELS[decorated["status"]]
    decorated["has_initial_result"] = bool(decorated.get("initial_result_path"))
    decorated["has_final_result"] = bool(decorated.get("final_result_path"))
    decorated["has_initial_upload"] = bool(decorated.get("initial_pdf_path"))
    decorated["has_supplement_upload"] = bool(decorated.get("supplement_pdf_path"))
    return decorated


def get_case(record_id: int) -> dict[str, Any] | None:
    data = _read_registry()
    stored = data["cases"].get(str(record_id))
    discovered = _discover_case_assets(record_id)

    if stored is None and not discovered:
        return None

    case = _default_case(record_id)
    if stored:
        case.update(stored)
    case.update(discovered)
    return _decorate_case(case)


def ensure_case(record_id: int) -> dict[str, Any]:
    data = _read_registry()
    stored = data["cases"].get(str(record_id))

    case = _default_case(record_id)
    if stored:
        case.update(stored)
    case.update(_discover_case_assets(record_id))

    if stored is None:
        created_at = case.get("created_at") or _now_str()
        case["created_at"] = created_at
        case["updated_at"] = created_at
    else:
        case["updated_at"] = _now_str()

    decorated = _decorate_case(case)
    data["cases"][str(record_id)] = _sanitize_case(decorated)
    _write_registry(data)
    return decorated


def create_case() -> dict[str, Any]:
    next_record_id = max(_known_record_ids() or {0}) + 1
    return ensure_case(next_record_id)


def update_case(record_id: int, **fields: Any) -> dict[str, Any]:
    data = _read_registry()
    current = data["cases"].get(str(record_id), _default_case(record_id))

    for key, value in fields.items():
        if key in CASE_FIELDS:
            current[key] = value

    if not current.get("created_at"):
        current["created_at"] = _now_str()
    current["updated_at"] = _now_str()

    merged = _default_case(record_id)
    merged.update(current)
    merged.update(_discover_case_assets(record_id))
    decorated = _decorate_case(merged)

    data["cases"][str(record_id)] = _sanitize_case(decorated)
    _write_registry(data)
    return decorated


def list_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for record_id in sorted(_known_record_ids(), reverse=True):
        case = get_case(record_id)
        if case:
            cases.append(case)
    return cases
