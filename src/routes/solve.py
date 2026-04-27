from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.models.models import Problem, Solution, Log
from src.services.ocr import extract_text_from_image
from src.services.interpreter import interpret_and_solve
from src.services.solver import solve_symbolic, solve_numeric, verify

router = APIRouter()

class TextInput(BaseModel):
    text: str

def _save_and_solve(problem_text: str, input_type: str, db: Session) -> dict:
    problem = Problem(input_type=input_type, input_data=problem_text)
    db.add(problem)
    db.flush()

    interpreted = interpret_and_solve(problem_text)
    equation    = interpreted.get("equation", "")

    sym = solve_symbolic(equation) if equation else {"status": "error", "result": "no equation"}
    num = solve_numeric(problem_text) if equation else {"status": "error", "result": "no equation"}
    verification_status = verify(sym, num)

    solution = Solution(
        problem_id=problem.id,
        interpreted_data={
            "type":      interpreted.get("type"),
            "variables": interpreted.get("variables"),
            "equation":  equation,
        },
        steps=interpreted.get("steps", []),
        final_answer=interpreted.get("final_answer", ""),
        verification_status=verification_status,
    )
    db.add(solution)
    db.commit()

    return {
        "status":          "success",
        "problem_text":    problem_text,
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
async def solve_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed = {"jpg", "jpeg", "png", "pdf"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()
    problem_text = extract_text_from_image(file_bytes, file.filename)

    if not problem_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from image")

    return _save_and_solve(problem_text, "image", db)

@router.post("/solve-text")
def solve_text(body: TextInput, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return _save_and_solve(body.text, "text", db)
