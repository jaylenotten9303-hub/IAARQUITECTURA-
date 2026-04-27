from sympy import symbols, Eq, solve, sympify, N
from sympy.parsing.sympy_parser import parse_expr
import re

def solve_symbolic(equation_str: str) -> dict:
    try:
        var_names = list(set(re.findall(r'\b[a-zA-Z]\b', equation_str)))
        var_symbols = {v: symbols(v) for v in var_names}

        if "=" in equation_str:
            lhs, rhs = equation_str.split("=", 1)
            lhs_expr = parse_expr(lhs.strip(), local_dict=var_symbols)
            rhs_expr = parse_expr(rhs.strip(), local_dict=var_symbols)
            eq = Eq(lhs_expr, rhs_expr)
            unknowns = [var_symbols[v] for v in var_names]
            solution = solve(eq, unknowns)
        else:
            expr = parse_expr(equation_str, local_dict=var_symbols)
            solution = float(N(expr))

        return {"status": "ok", "result": str(solution)}
    except Exception as e:
        return {"status": "error", "result": str(e)}

def solve_numeric(equation_str: str) -> dict:
    try:
        substituted = re.sub(r'[a-zA-Z_]\w*\s*=\s*[\d.]+', '', equation_str)
        pairs = re.findall(r'([a-zA-Z_]\w*)\s*=\s*([\d.]+)', equation_str)
        local = {k: float(v) for k, v in pairs}

        formula_match = re.search(r'[a-zA-Z_]\w*\s*=\s*(.+)', equation_str)
        if formula_match:
            expr_str = formula_match.group(1)
            result = eval(expr_str, {"__builtins__": {}}, local)
            return {"status": "ok", "result": result}

        return {"status": "error", "result": "Could not parse numeric expression"}
    except Exception as e:
        return {"status": "error", "result": str(e)}

def verify(sym_result: dict, num_result: dict) -> str:
    try:
        if sym_result["status"] == "error" or num_result["status"] == "error":
            return "unverified"
        sym_val = float(str(sym_result["result"]).strip("[]{}").split(",")[0])
        num_val = float(str(num_result["result"]))
        if abs(sym_val - num_val) < 0.01:
            return "valid"
        return "mismatch"
    except Exception:
        return "unverified"
