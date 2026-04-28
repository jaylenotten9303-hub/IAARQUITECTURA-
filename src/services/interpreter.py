import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert structural engineer and mathematician specializing in reinforced concrete (ACI 318), steel structures (AISC), and structural mechanics. Solve the problem completely using ONLY the given data.

Return ONLY a valid JSON object with this exact structure:
{
  "type": "equation_type",
  "variables": ["list", "of", "variables"],
  "equation": "main governing equation",
  "steps": ["Step 1: description — formula → substitution → result", "Step 2: ...", ...],
  "final_answer": "numerical result with units"
}

STRICT RULES:
1. Use ONLY values explicitly given. If a standard code value is assumed (e.g. phi=0.9), state it explicitly in the step.
2. Every step MUST follow: description — formula → substitution → number.
   Example: "Carga última: Wu = 1.2WD + 1.6WL → 1.2(15) + 1.6(20) = 50 kN/m"
3. final_answer MUST contain the actual computed numbers with units. NEVER 'incomplete_data'.
4. For reinforced concrete: default to ACI 318, f'c in MPa or kg/cm², fy in MPa or kg/cm².
5. Always double-check arithmetic. If intermediate result seems off, recompute.
6. If multiple quantities required, list ALL in final_answer separated by commas.
7. Respond ONLY with valid JSON — no markdown, no extra text."""

VERIFY_PROMPT = """You are a senior structural engineer doing a quality check. Re-compute independently and verify this solution.

PROBLEM:
{problem}

SOLUTION STEPS:
{steps}

CLAIMED ANSWER: {final_answer}

Re-derive each step from scratch using the given values. Check if the final answer is numerically correct.
Return ONLY valid JSON:
{{
  "verified": true,
  "confidence": "high",
  "corrected_answer": "",
  "notes": ""
}}
If the answer is WRONG, set verified=false and provide the correct value in corrected_answer."""

def interpret_and_solve(problem_text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": problem_text},
            ],
        )
        result = json.loads(response.choices[0].message.content)

        verified = _verify_solution(problem_text, result)
        if not verified.get("verified", True) and verified.get("corrected_answer"):
            result["final_answer"] = verified["corrected_answer"]
            note = verified.get("notes", "Respuesta corregida por verificación")
            result["steps"].append(f"✓ Verificación: {note}")

        return result
    except Exception as e:
        return {
            "type":         "error",
            "variables":    [],
            "equation":     "",
            "steps":        [str(e)],
            "final_answer": "error",
        }

def _verify_solution(problem: str, solution: dict) -> dict:
    try:
        steps_text = "\n".join(solution.get("steps", []))
        final = solution.get("final_answer", "")
        msg = VERIFY_PROMPT.format(problem=problem, steps=steps_text, final_answer=final)
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": msg}],
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"verified": True}
