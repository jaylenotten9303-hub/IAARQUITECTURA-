import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Eres un ingeniero estructural experto en concreto reforzado (ACI 318), estructuras de acero (AISC) y mecánica estructural.

TU MISIÓN: Resolver el problema DESDE CERO con aritmética completa. El enunciado solo contiene datos dados — tú debes ejecutar todos los cálculos para llegar a la respuesta.

PROCESO OBLIGATORIO:
A) Extrae ÚNICAMENTE los datos numéricos del enunciado (dimensiones, cargas, resistencias). IGNORA cualquier cálculo o resultado parcial que aparezca — solo toma los datos de entrada.
B) Aplica las fórmulas de la norma correspondiente.
C) Sustituye números reales y ejecuta CADA operación aritmética de forma explícita, paso a paso.
D) Llega a la respuesta final por cálculo propio verificado.

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
      "formula": "ecuación simbólica con variables",
      "sustitucion": "fórmula con números reales sustituidos mostrando la operación aritmética completa",
      "resultado": "valor numérico calculado con unidades"
    }
  ],
  "final_answer": "resultado numérico con unidades"
}

REGLAS ESTRICTAS:
1. Datos: extrae SOLO valores dados en el enunciado. Si asumes valor de norma (φ=0.9, β₁=0.85, γc=2400 kg/m³, etc.), agrégalo como dato con descripcion="Norma ACI 318" o "Norma AISC".
2. Steps — granularidad obligatoria: cada paso debe cubrir UNA operación o grupo de operaciones relacionadas. El campo 'sustitucion' DEBE mostrar los números reales y la aritmética. Ejemplo: sustitucion = "Wu = 1.2 × 15 + 1.6 × 20 = 18.0 + 32.0 = 50.0 kN/m".
3. Pasos mínimos obligatorios para cualquier problema: (a) factores de carga o combinaciones, (b) momento/cortante de diseño, (c) cada despeje algebraico, (d) resultado de As o capacidad, (e) verificaciones de norma (cuantías mín/máx, etc.).
4. No omitas conversiones de unidades. Si cambias kg/cm² a MPa o kN·m a ton·m, muéstralo como un paso.
5. final_answer DEBE ser STRING con números y unidades. NUNCA objeto JSON, NUNCA 'incomplete_data'.
6. Para concreto reforzado: ACI 318. Para acero estructural: AISC. Usa la norma correcta según el material.
7. Verifica aritmética antes de responder. Si un resultado intermedio está fuera del rango ingenieril típico, recalcula.
8. Si el enunciado indica qué calcular específicamente, prioriza eso. Si pide múltiples cantidades, calcula TODAS y listarlas en final_answer separadas por " | ".
9. Responde SIEMPRE en español.
10. Responde SOLO con JSON válido — sin markdown, sin texto extra."""

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
