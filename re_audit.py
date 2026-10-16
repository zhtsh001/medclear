import os
from google import genai
from google.genai import types
import pathlib
import json
import re
from datetime import datetime

def _client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY before running an audit.")
    return genai.Client(api_key=api_key)


def print_final_report(result, filename):
    print("\n" + "█" * 60)
    print("       🛡️  MEDCLEAR: FULL HISTORY RECONCILIATION       ")
    print(f"       Final Report: {filename}")
    print("█" * 60)

    status = "✅ FULLY COMPLIANT" if result.get("is_compliant") else "⚠️ NON-COMPLIANT"
    print(f"Overall Status: {status}")
    print(f"Confidence Score: {result.get('confidence_score', 0):.2f}")

    if result.get("inferred_intake_semester"):
        print(f"Inferred Intake: {result['inferred_intake_semester']}")

    print(f"\n[Verification Details]")
    print(f"Authenticity: {result.get('authenticity_check', 'N/A')}")

    doses = result.get("all_doses_extracted", [])
    if doses:
        print(f"\n[Vaccination Timeline (Merged from all docs)]")
        for d in doses:
            print(f"- {d.get('vaccine')}: Date {d.get('date')} (Source: {d.get('source_doc')})")

    if not result.get("is_compliant"):
        print(f"\n[Remaining Deficiencies]")
        for idx, issue in enumerate(result.get("issues", []), 1):
            print(f"{idx}. {issue.get('vaccine')}: {issue.get('reason')}")
            print(f"   Required: {issue.get('remedy')}")
    else:
        print(f"\n✨ Reconciliation Successful: All requirements met across multiple documents.")

    print("█" * 60 + "\n")


def run_re_audit(original_pdf_path, supplement_pdf_path, policy_json_path, student_age):
    current_date = datetime.now().strftime("%Y-%m-%d")

    orig_path = pathlib.Path(original_pdf_path)
    supp_path = pathlib.Path(supplement_pdf_path)

    match = re.search(r'\d+', supp_path.stem)
    record_num = match.group() if match else "X"
    univ_prefix = pathlib.Path(policy_json_path).stem.split('_')[0]
    output_filename = f"{univ_prefix}_Record{record_num}_Final_Audit.json"

    with open(policy_json_path, "r") as f:
        policy_context = f.read()

    prompt = f"""
    ROLE: Senior University Medical Compliance Officer.

    AUXILIARY INFO:
    - Current System Date: {current_date}
    - Student Age: {student_age} years old.

    CONTEXT:
    The student has submitted TWO documents for review:
    1. ORIGINAL_RECORD: The initial submission.
    2. SUPPLEMENTARY_MATERIAL: New evidence (e.g., missing MMR dose or new TB test).

    UNIVERSITY VACCINE POLICY:
    {policy_context}

    LOGIC FOR TB BLOOD TEST (QuantiFERON/T-SPOT):
    Apply dynamic logic based on {current_date}:
    1. If the audit occurs in late Fall/Winter, assume SPRING intake (TB test after Dec 21st).
    2. If the audit occurs in Spring/Summer, assume FALL intake (TB test after July 21st).
    3. Use the 'Current System Date' to infer the semester and judge the TB test date fairly.

    TASK:
    1. EXTRACT ALL immunization/test dates from BOTH attached documents.
    2. MERGE into a single timeline. If MMR Dose 1 is in Original and Dose 2 is in Supplement, they now have 2 doses.
    3. VALIDATE:
       - Dose Counts & Intervals (e.g., MMR doses must be >= 28 days apart).
       - Age constraints (e.g., MMR after age 1).
       - TB test validity based on the inferred intake semester.
    4. AUTHENTICITY: Inspect stamps/seals on BOTH documents.

    OUTPUT FORMAT: Return a JSON object ONLY:
    - confidence_score: (0.0 to 1.0)
    - is_compliant: (boolean)
    - inferred_intake_semester: (e.g., "Fall 2026")
    - all_doses_extracted: (list of objects: {{"vaccine": "...", "date": "...", "source_doc": "original/supplement"}})
    - authenticity_check: (string description)
    - issues: (list of objects with 'vaccine', 'reason', 'remedy', empty if compliant)
    """

    print(f"🚀 Re-auditing: Merging {orig_path.name} and {supp_path.name} | System Date: {current_date}")

    response = None
    try:
        response = _client().models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            contents=[
                types.Part.from_bytes(data=orig_path.read_bytes(), mime_type='application/pdf'),
                types.Part.from_bytes(data=supp_path.read_bytes(), mime_type='application/pdf'),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )

        result = json.loads(response.text)

        with open(output_filename, "w") as f:
            json.dump(result, f, indent=4)

        print_final_report(result, output_filename)
        return result

    except Exception as e:
        print(f"❌ Error during reconciliation: {e}")
        if hasattr(response, 'text'):
            print("Raw output:", response.text)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Review an original and supplementary authorized PDF.")
    parser.add_argument("--original", required=True)
    parser.add_argument("--supplement", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--age", required=True, type=int)
    args = parser.parse_args()
    run_re_audit(args.original, args.supplement, args.policy, args.age)

