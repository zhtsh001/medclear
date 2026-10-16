from __future__ import annotations

from pathlib import Path
import os
import secrets

from flask import Flask, flash, redirect, render_template, request, url_for

from services.audit_bridge import load_result_json, run_final_audit, run_initial_audit
from services.case_registry import create_case, ensure_case, get_case, list_cases, update_case

ROOT_DIR = Path(__file__).resolve().parent
INITIAL_UPLOAD_DIR = ROOT_DIR / "Immunization_Records"

app = Flask(__name__)
app.secret_key = os.environ.get("MEDCLEAR_SESSION_SECRET") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def _parse_age(raw_value: str) -> int | None:
    if not raw_value:
        return None

    try:
        age = int(raw_value)
    except ValueError:
        return None

    if age <= 0 or age > 120:
        return None

    return age


def _is_pdf_upload(filename: str | None) -> bool:
    return bool(filename and filename.lower().endswith(".pdf"))


@app.route("/")
def index():
    return render_template("index.html", cases=list_cases())


@app.post("/cases/new")
def new_case():
    case = create_case()
    flash(f"Created new case: Record{case['record_id']}", "success")
    return redirect(url_for("view_case", record_id=case["record_id"]))


@app.post("/cases/open")
def open_case():
    raw_record_id = (request.form.get("record_id") or "").strip()

    try:
        record_id = int(raw_record_id)
    except ValueError:
        flash("Please enter a valid record number.", "error")
        return redirect(url_for("index"))

    case = get_case(record_id)
    if case is None:
        flash("That case does not exist yet. Create a new one first.", "error")
        return redirect(url_for("index"))

    return redirect(url_for("view_case", record_id=record_id))


@app.get("/cases/<int:record_id>")
def view_case(record_id: int):
    case = get_case(record_id)
    if case is None:
        flash("That case was not found.", "error")
        return redirect(url_for("index"))

    initial_result = load_result_json(case.get("initial_result_path"))
    final_result = load_result_json(case.get("final_result_path"))
    return render_template(
        "case.html",
        case=case,
        initial_result=initial_result,
        final_result=final_result,
    )


@app.post("/cases/<int:record_id>/initial-upload")
def upload_initial(record_id: int):
    case = ensure_case(record_id)
    uploaded_file = request.files.get("initial_pdf")
    student_age = _parse_age((request.form.get("student_age") or "").strip())

    if student_age is None:
        flash("Please enter a valid student age.", "error")
        return redirect(url_for("view_case", record_id=record_id))

    if not uploaded_file or not _is_pdf_upload(uploaded_file.filename):
        flash("Please upload a PDF file for the initial record.", "error")
        return redirect(url_for("view_case", record_id=record_id))

    initial_path = INITIAL_UPLOAD_DIR / f"Record{record_id}.pdf"
    INITIAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_file.save(initial_path)

    update_case(
        record_id,
        age=student_age,
        initial_pdf_path=initial_path.relative_to(ROOT_DIR).as_posix(),
        initial_error=None,
    )

    audit_meta = run_initial_audit(record_id, student_age)
    update_case(
        record_id,
        age=student_age,
        initial_pdf_path=initial_path.relative_to(ROOT_DIR).as_posix(),
        initial_result_path=audit_meta["output_path"],
        initial_result_source=audit_meta["source"],
        initial_error=audit_meta["error"],
    )

    if audit_meta["source"] == "live":
        flash(f"Initial audit finished for Record{record_id}.", "success")
    else:
        flash(
            f"Initial audit used sample fallback for Record{record_id}. "
            "The page still shows the full demo result flow.",
            "warning",
        )

    return redirect(url_for("view_case", record_id=record_id))


@app.post("/cases/<int:record_id>/supplement-upload")
def upload_supplement(record_id: int):
    case = ensure_case(record_id)
    uploaded_file = request.files.get("supplement_pdf")
    age_raw_value = (request.form.get("student_age") or str(case.get("age") or "")).strip()
    student_age = _parse_age(age_raw_value)

    if not case.get("initial_pdf_path"):
        flash("Please upload the initial immunization record first.", "error")
        return redirect(url_for("view_case", record_id=record_id))

    if student_age is None:
        flash("Please enter a valid student age for the final audit.", "error")
        return redirect(url_for("view_case", record_id=record_id))

    if not uploaded_file or not _is_pdf_upload(uploaded_file.filename):
        flash("Please upload a PDF file for the supplementary material.", "error")
        return redirect(url_for("view_case", record_id=record_id))

    supplement_path = INITIAL_UPLOAD_DIR / f"Supplementary_Materials{record_id}.pdf"
    INITIAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_file.save(supplement_path)

    update_case(
        record_id,
        age=student_age,
        supplement_pdf_path=supplement_path.relative_to(ROOT_DIR).as_posix(),
        final_error=None,
    )

    audit_meta = run_final_audit(record_id, student_age)
    update_case(
        record_id,
        age=student_age,
        supplement_pdf_path=supplement_path.relative_to(ROOT_DIR).as_posix(),
        final_result_path=audit_meta["output_path"],
        final_result_source=audit_meta["source"],
        final_error=audit_meta["error"],
    )

    if audit_meta["source"] == "live":
        flash(f"Final audit finished for Record{record_id}.", "success")
    else:
        flash(
            f"Final audit used sample fallback for Record{record_id}. "
            "The page still shows the complete reconciliation flow.",
            "warning",
        )

    return redirect(url_for("view_case", record_id=record_id))


if __name__ == "__main__":
    app.run(debug=False)
