import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert in structural engineering and mathematics.
Given a problem, return a JSON with:
{
  "type": "equation_type",
  "variables": ["list", "of", "variables"],
  "equation": "main equation as string",
  "steps": ["step 1", "step 2", ...],
  "final_answer": "result with units"
}
Be precise. Never fabricate values. If data is missing, set final_answer to 'incomplete_data'."""

def interpret_and_solve(problem_text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": problem_text},
            ],
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "type":         "error",
            "variables":    [],
            "equation":     "",
            "steps":        [str(e)],
            "final_answer": "error",
        }
