import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert structural engineer and mathematician. Solve the problem completely using the given data.

Return a JSON with this exact structure:
{
  "type": "equation_type",
  "variables": ["list", "of", "variables"],
  "equation": "main governing equation",
  "steps": ["Step 1: description with calculated value", "Step 2: ...", ...],
  "final_answer": "numerical result with units, e.g. Mu = 450 kN·m, As = 12.5 cm²"
}

Rules:
- Substitute ALL given numeric values and compute the final number.
- Each step must show the substitution and result, e.g. "U = 1.2(15) + 1.6(20) = 50 kN/m".
- final_answer must contain the actual computed number with units — NEVER return 'incomplete_data' when values are provided.
- If multiple answers are required, list them all in final_answer separated by commas.
- Respond only with valid JSON."""

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
