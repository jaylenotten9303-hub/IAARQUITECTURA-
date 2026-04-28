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

REGLAS ESTRICTAS:
1. Usa SOLO los valores dados explícitamente. Si asumes un valor de norma (ej. phi=0.9), indícalo en el paso.
2. Cada paso DEBE seguir: descripción — fórmula → sustitución → número.
   Ejemplo: "Carga última: Wu = 1.2WD + 1.6WL → 1.2(15) + 1.6(20) = 50 kN/m"
3. final_answer DEBE contener los números calculados con unidades. NUNCA 'incomplete_data'.
4. Para concreto reforzado: norma ACI 318 por defecto, f'c en kg/cm² o MPa, fy en kg/cm² o MPa.
5. Verifica la aritmética. Si un resultado intermedio parece incorrecto, recalcula.
6. Si se piden múltiples cantidades, lista TODAS en final_answer separadas por comas.
7. Responde SIEMPRE en español.
8. Responde SOLO con JSON válido — sin markdown, sin texto extra."""

VERIFY_PROMPT = """Eres un ingeniero estructural senior haciendo una revisión de calidad. Recalcula de forma independiente y verifica esta solución.

PROBLEMA:
{problem}

PASOS DE LA SOLUCIÓN:
{steps}

RESPUESTA DECLARADA: {final_answer}

Recalcula cada paso desde cero usando los valores dados. Verifica si la respuesta final es numéricamente correcta.
Devuelve SOLO JSON válido:
{{
  "verified": true,
  "confidence": "high",
  "corrected_answer": "",
  "notes": ""
}}
Si la respuesta es INCORRECTA, pon verified=false y la respuesta corregida en corrected_answer.
Responde SIEMPRE en español."""

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
