from google import genai
from google.genai import types
import json
import os
from pathlib import Path

def _client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY before running an audit.")
    return genai.Client(api_key=api_key)

extract_vaccine_requirements_schema = {
    "name": "extract_vaccine_requirements",
    "description": "Extracts university immunization requirements into a structured format for auditing.",
    "parameters": {
        "type": "object",
        "properties": {
            "university_policy": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "vaccine_name": {"type": "string", "description": "e.g., MMR, Tdap, Meningococcal"},
                        "required_doses": {"type": "integer", "description": "Total number of doses needed."},
                        "intervals": {"type": "string", "description": "Time between doses (e.g., '1-6 months')."},
                        "age_or_date_constraints": {"type": "string",
                                                    "description": "Specific rules like 'after age 1' or 'after July 21'."},
                        "validity_period": {"type": "string", "description": "e.g., 'within the past 10 years'."},
                        "target_audience": {"type": "string", "enum": ["All Students", "International Students"]}
                    },
                    "required": ["vaccine_name", "required_doses", "target_audience"]
                }
            }
        },
        "required": ["university_policy"],
    },
}

tools = [types.Tool(function_declarations=[extract_vaccine_requirements_schema])]
config = types.GenerateContentConfig(
    tools=tools,
    temperature=0.1,
    response_mime_type="application/json"
)


def run_policy_extraction():
    try:
        with open("IIT_policy.txt", "r", encoding="utf-8") as f:
            policy_text = f.read()
    except FileNotFoundError:
        print("Error: IIT_policy.txt was not found in the directory.")
        return

    print("Sending policy to Gemini for extraction...")

    prompt = f"Analyze the following university vaccine policy and extract the requirements:\n\n{policy_text}"

    response = _client().models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        contents=prompt,
        config=config,
    )

    first_part = response.candidates[0].content.parts[0]

    if first_part.function_call:
        extracted_data = first_part.function_call.args

        output_filename = Path(__file__).with_name("IIT_vaccine_policy.json")
        with open(output_filename, "w", encoding="utf-8") as json_file:
            json.dump(extracted_data, json_file, indent=4)

        print(f"Success! Data saved to {output_filename}")
        print(json.dumps(extracted_data, indent=4))
    else:
        print("The model did not trigger the function call. Raw response:")
        print(response.text)


if __name__ == "__main__":
    run_policy_extraction()
