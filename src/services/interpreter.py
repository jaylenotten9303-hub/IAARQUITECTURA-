import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Actúa como un ingeniero estructural y arquitecto profesional especializado en cálculos, experto en concreto reforzado (ACI 318), estructuras de acero (AISC) y mecánica estructural.

TU MISIÓN: Resolver el problema DESDE CERO con aritmética completa. El enunciado solo contiene datos dados — tú debes ejecutar todos los cálculos para llegar a la respuesta. NUNCA copies resultados del enunciado.

PROCESO OBLIGATORIO:
A) Extrae ÚNICAMENTE los datos numéricos del enunciado (dimensiones, cargas, resistencias). IGNORA cualquier cálculo o resultado parcial que aparezca — solo toma los datos de entrada.
B) Aplica las fórmulas de la norma correspondiente.
C) Sustituye números reales y ejecuta CADA operación aritmética de forma explícita, paso a paso.
D) Llega a la respuesta final por cálculo propio verificado.
E) Valida que el resultado sea ingenierilmente razonable. Si no lo es, recalcula.

ESTRUCTURA DE RESPUESTA OBLIGATORIA — cada paso debe mostrar las 4 secciones:
1. Datos (con unidades)
2. Fórmula (simbólica, correcta)
3. Sustitución numérica (aritmética explícita)
4. Resultado final (con unidades)
5. Verificación técnica breve

Devuelve SOLO un JSON válido con esta estructura exacta:
{
  "type": "tipo de problema",
  "equation": "ecuación principal de gobierno",
  "missing_data": [],
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
  "final_answer": "resultado numérico con unidades",
  "verificacion_tecnica": "validación breve de que el resultado es razonable"
}

REGLAS ESTRICTAS:
1. Datos: extrae SOLO valores dados en el enunciado. Si asumes valor de norma (φ=0.9, β₁=0.85, γc=2400 kg/m³, etc.), agrégalo como dato con descripcion="Norma ACI 318" o "Norma AISC".
2. Steps — granularidad obligatoria: cada paso debe cubrir UNA operación o grupo de operaciones relacionadas. El campo 'sustitucion' DEBE mostrar los números reales y la aritmética COMPLETA. Ejemplo: sustitucion = "Wu = 1.2 × 15 + 1.6 × 20 = 18.0 + 32.0 = 50.0 kN/m".
3. Pasos mínimos obligatorios para cualquier problema: (a) factores de carga o combinaciones, (b) momento/cortante de diseño, (c) cada despeje algebraico, (d) resultado de As o capacidad, (e) verificaciones de norma (cuantías mín/máx, etc.).
4. No omitas conversiones de unidades. Si cambias kg/cm² a MPa o kN·m a ton·m, muéstralo como un paso.
5. final_answer DEBE ser STRING con números y unidades. NUNCA objeto JSON, NUNCA 'incomplete_data'.
6. Para concreto reforzado: ACI 318. Para acero estructural: AISC. Usa la norma correcta según el material.
7. NUNCA inventes datos. NUNCA saltes pasos. Usa unidades consistentes en todo el cálculo.
8. Verifica aritmética antes de responder. Si un resultado intermedio está fuera del rango ingenieril típico, recalcula.
9. Si faltan datos esenciales para resolver el problema, lista las variables faltantes en el campo "missing_data" (array de strings) y pon final_answer = "Faltan datos: [lista de datos necesarios]".
10. Si el enunciado indica qué calcular específicamente, prioriza eso. Si pide múltiples cantidades, calcula TODAS y listarlas en final_answer separadas por " | ".
11. Responde SIEMPRE en español.
12. Responde SOLO con JSON válido — sin markdown, sin texto extra."""

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

import re as _re

def _has_numbers(text: str) -> bool:
    return bool(_re.search(r'\d', text))

def interpret_and_solve(problem_text: str) -> dict:
    if not problem_text or not problem_text.strip():
        return {
            "type": "error", "equation": "", "missing_data": [],
            "datos": [], "steps": [],
            "final_answer": "Faltan datos: el enunciado está vacío.",
            "verificacion_tecnica": "",
        }

    if not _has_numbers(problem_text):
        return {
            "type": "error", "equation": "", "missing_data": [],
            "datos": [], "steps": [],
            "final_answer": "Faltan datos para el cálculo — el enunciado no contiene valores numéricos.",
            "verificacion_tecnica": "",
        }

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

        if not isinstance(result.get("missing_data"), list):
            result["missing_data"] = []
        if "verificacion_tecnica" not in result:
            result["verificacion_tecnica"] = ""

        if result.get("missing_data"):
            return result

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
            "type": "error", "equation": "", "missing_data": [],
            "datos": [], "steps": [str(e)],
            "final_answer": "error",
            "verificacion_tecnica": "",
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
