import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Eres un ingeniero estructural experto en concreto reforzado (ACI 318), estructuras de acero (AISC) y mecánica estructural. Resuelve el problema completamente usando SOLO los datos proporcionados.

Devuelve SOLO un JSON válido con esta estructura exacta:
{
  "type": "tipo de problema",
  "equation": "ecuación principal de gobierno",
  "datos": [
    {"variable": "símbolo", "valor": "número con unidades", "descripcion": "nombre del dato"}
  ],
  "steps": [
    {
      "descripcion": "qué se calcula en este paso",
      "formula": "ecuación simbólica",
      "sustitucion": "números sustituidos",
      "resultado": "valor calculado con unidades"
    }
  ],
  "final_answer": "resultado numérico con unidades"
}

REGLAS ESTRICTAS:
1. Usa SOLO los valores dados. Si asumes un valor de norma (ej. φ=0.9), ponlo como dato con descripcion="Norma ACI 318".
2. Cada step DEBE tener los 4 campos: descripcion, formula, sustitucion, resultado.
3. final_answer DEBE tener los números calculados con unidades. NUNCA 'incomplete_data'.
4. Para concreto reforzado: norma ACI 318, f'c en kg/cm² o MPa, fy en kg/cm² o MPa.
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
            result["steps"].append({
                "descripcion": "Verificación automática",
                "formula": "—",
                "sustitucion": note,
                "resultado": verified["corrected_answer"],
            })

        return result
    except Exception as e:
        return {
            "type":         "error",
            "variables":    [],
            "equation":     "",
            "steps":        [str(e)],
            "final_answer": "error",
        }

def _steps_to_text(steps: list) -> str:
    lines = []
    for i, s in enumerate(steps, 1):
        if isinstance(s, dict):
            lines.append(f"{i}. {s.get('descripcion','')} | {s.get('formula','')} | {s.get('sustitucion','')} = {s.get('resultado','')}")
        else:
            lines.append(f"{i}. {s}")
    return "\n".join(lines)

def _verify_solution(problem: str, solution: dict) -> dict:
    try:
        steps_text = _steps_to_text(solution.get("steps", []))
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
