from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.models.models import Problem, Solution, Log
from src.services.ocr import extract_text_from_images, MAX_IMAGES
from src.services.interpreter import interpret_and_solve
from src.services.solver import solve_symbolic, solve_numeric, verify

router = APIRouter()

ALLOWED_EXT = {"jpg", "jpeg", "png"}

class TextInput(BaseModel):
    text: str

def _save_and_solve(problem_text: str, input_type: str, db: Session) -> dict:
    problem = Problem(input_type=input_type, input_data=problem_text)
    db.add(problem)
    db.flush()

    interpreted = interpret_and_solve(problem_text)
    equation    = interpreted.get("equation", "")

    # GPT-4o sometimes returns dicts instead of strings — sanitize
    raw_answer = interpreted.get("final_answer", "")
    if isinstance(raw_answer, dict):
        raw_answer = ", ".join(f"{k} = {v}" for k, v in raw_answer.items())
    elif not isinstance(raw_answer, str):
        raw_answer = str(raw_answer)

    raw_steps = interpreted.get("steps", [])
    clean_steps = []
    for s in raw_steps:
        if isinstance(s, dict):
            r = s.get("resultado", "")
            clean_steps.append({**s, "resultado": r if isinstance(r, str) else str(r)})
        else:
            clean_steps.append(str(s))

    sym = solve_symbolic(equation) if equation else {"status": "error", "result": "no equation"}
    num = solve_numeric(problem_text) if equation else {"status": "error", "result": "no equation"}
    verification_status = verify(sym, num)

    solution = Solution(
        problem_id=problem.id,
        interpreted_data={
            "type":      interpreted.get("type"),
            "variables": interpreted.get("variables"),
            "equation":  equation,
            "datos":     interpreted.get("datos", []),
        },
        steps=clean_steps,
        final_answer=raw_answer,
        verification_status=verification_status,
    )
    db.add(solution)
    db.commit()

    return {
        "status":           "success",
        "problem_text":     problem_text,
        "interpreted_data": solution.interpreted_data,
        "solution": {
            "steps":        solution.steps,
            "final_answer": solution.final_answer,
        },
        "verification": {
            "method_1": "symbolic",
            "method_2": "numeric",
            "result":   verification_status,
        },
    }

@router.post("/solve")
async def solve_image(
    files: List[UploadFile] = File(...),
    question: str = Form(""),
    db: Session = Depends(get_db),
):
    if len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_IMAGES} imágenes por solicitud.")

    file_data = []
    for f in files:
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"Tipo no soportado: {f.filename}. Usa JPG o PNG.")
        file_data.append((await f.read(), f.filename))

    try:
        problem_text = extract_text_from_images(file_data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not problem_text.strip():
        raise HTTPException(status_code=422, detail="No se pudo extraer texto de las imágenes.")

    if question.strip():
        problem_text += f"\n\nEl usuario necesita calcular específicamente: {question.strip()}"

    return _save_and_solve(problem_text, "image", db)

@router.post("/solve-text")
def solve_text(body: TextInput, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return _save_and_solve(body.text, "text", db)
