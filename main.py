import os
from google import genai
from google.genai import types
import pathlib
import json
from datetime import datetime

def _client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY before running an audit.")
    return genai.Client(api_key=api_key)


def print_human_readable_report(result, filename):
    print("\n" + "=" * 50)
    print("       🎓 MEDCLEAR AUDIT REPORT       ")
    print(f"       File: {filename}")
    print("=" * 50)

    status = "✅ COMPLIANT" if result.get("is_compliant") else "❌ NON-COMPLIANT"
    print(f"Overall Status: {status}")

    confidence = result.get("confidence_score", 0)
    print(f"Confidence Score: {confidence:.2f} / 1.0")

    print(f"\n[Authenticity Check]")
    print(f"Details: {result.get('authenticity_check', 'N/A')}")

    issues = result.get("issues", [])
    if not result.get("is_compliant") and issues:
        print(f"\n[Identified Issues & Remedies]")
        for idx, issue in enumerate(issues, 1):
            print(f"{idx}. Vaccine: {issue.get('vaccine')}")
            print(f"   Reason:  {issue.get('reason')}")
            print(f"   Remedy:  {issue.get('remedy')}")
    elif result.get("is_compliant"):
        print(f"\n✨ All records match the University's policy perfectly.")

    print("=" * 50 + "\n")


def audit_student_record(pdf_path, policy_json_path, student_age):
    current_date = datetime.now().strftime("%Y-%m-%d")

    record_name = pathlib.Path(pdf_path).stem
    univ_prefix = pathlib.Path(policy_json_path).stem.split('_')[0]
    output_filename = f"{univ_prefix}_{record_name}_Result.json"

    with open(policy_json_path, "r") as f:
        policy_context = f.read()

    file_path = pathlib.Path(pdf_path)

    prompt = f"""
    ROLE: Senior University Medical Compliance Officer.

    AUXILIARY INFO:
    - Current System Date: {current_date}
    - Student Age: {student_age} years old.

    CONTEXT (University Vaccine Policy):
    {policy_context}

    LOGIC FOR TB BLOOD TEST (QuantiFERON/T-SPOT):
    The policy mentions July 21st for Fall intake. However, apply the following dynamic logic:
    1. If the student is enrolling for SPRING (current date is late Fall/Winter), the TB test must typically be taken after December 21st of the previous year (or follow a similar 6-month recency rule).
    2. If the student is enrolling for FALL (current date is Spring/Summer), the July 21st rule in the policy applies.
    3. Use the 'Current System Date' to infer which semester the audit is likely for and judge the TB test date fairly.

    INSTRUCTIONS:
    1. EXTRACT ALL DATES: Identify every single vaccination date and TB test date from the PDF.
    2. CROSS-CHECK: 
       - MMR: REQUIRES a TWO-DOSE series. Check if Dose 1 was given after age 1.
       - TB Test: Evaluate validity based on the inferred intake semester and the July 21st (Fall) or December 21st (Spring) logic.
    3. AUTHENTICITY: Look for the 'Clinic Stamp' or 'Official Seal'.

    OUTPUT FORMAT: Return a JSON object ONLY:
    - confidence_score: (0.0 to 1.0)
    - is_compliant: (boolean)
    - inferred_intake_semester: (string, e.g., "Fall 2026" or "Spring 2026")
    - extracted_vaccinations: (list of vaccines and dates found)
    - authenticity_check: (string description)
    - issues: (list of objects with 'vaccine', 'reason', and 'remedy')
    """

    print(f"🚀 Analyzing {record_name} (Age: {student_age}) | System Date: {current_date}")

    response = _client().models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        contents=[
            types.Part.from_bytes(data=file_path.read_bytes(), mime_type='application/pdf'),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )

    try:
        result = json.loads(response.text)
        with open(output_filename, "w") as f:
            json.dump(result, f, indent=4)

        print(f"Audit Complete. Result saved to: {output_filename}")
        print_human_readable_report(result, output_filename)
        print(f"Inferred Intake: {result.get('inferred_intake_semester', 'Unknown')}")
        return result
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(response.text)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Audit an authorized PDF against a supplied policy.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--age", required=True, type=int)
    args = parser.parse_args()
    audit_student_record(args.pdf, args.policy, args.age)

