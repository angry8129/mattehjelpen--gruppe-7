"""Numerisk kontroll av løsninger uten å gi falsk verifisering."""

from __future__ import annotations

import random
import re
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import convert_xor, implicit_multiplication_application, parse_expr, standard_transformations


_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
TOLERANSE = 1e-8


def _expression(value: str, variable: str = "x") -> sp.Expr:
    symbol = sp.Symbol(variable)
    return parse_expr(value, local_dict={variable: symbol}, transformations=_TRANSFORMATIONS)


def _points(problem: str, solution: str) -> list[float]:
    generator = random.Random(f"{problem}\0{solution}")
    return [round(generator.uniform(-3, 3), 6) for _ in range(3)]


def _numeric_equal(left: Any, right: Any, variable: sp.Symbol, point: float) -> bool:
    left_value = complex(sp.N(left.subs(variable, point), 15))
    right_value = complex(sp.N(right.subs(variable, point), 15))
    return abs(left_value - right_value) <= TOLERANSE


def _validate_derivative(problem: str, solution: str, variable: str) -> dict[str, Any]:
    expression_text = re.sub(r"^(deriver|differentier|derivér|deriv)\s*", "", problem, flags=re.IGNORECASE).strip()
    expected = _expression(expression_text, variable)
    actual = _expression(solution, variable)
    symbol = sp.Symbol(variable)
    expected = sp.diff(expected, symbol)
    points = _points(problem, solution)
    checks = [_numeric_equal(expected, actual, symbol, point) for point in points]
    return {
        "validert": all(checks),
        "detaljer": (
            f"SymPy sammenlignet den beregnede deriverte med løsningen "
            f"i punktene {points} med toleranse {TOLERANSE}. Resultater: {checks}."
        ),
    }


def _validate_equation(problem: str, solution: str, variable: str) -> dict[str, Any]:
    if "=" in problem:
        left_text, right_text = problem.split("=", 1)
    else:
        left_text, right_text = problem, "0"
    left = _expression(re.sub(r"^(løs|solve|finn)\s*", "", left_text, flags=re.IGNORECASE), variable)
    right = _expression(right_text, variable)
    symbol = sp.Symbol(variable)
    values = sp.solve(sp.Eq(left, right), symbol)
    supplied = sp.sympify(solution, locals={variable: symbol})
    supplied_values = supplied if isinstance(supplied, list) else [supplied]
    if not values or set(supplied_values) != set(values):
        return {"validert": False, "detaljer": "Løsningen samsvarer ikke med SymPy sine løsninger."}
    points = _points(problem, solution)
    residuals = [sp.N((left - right).subs(symbol, value), 15) for value in supplied_values]
    checks = [abs(complex(residual)) <= TOLERANSE for residual in residuals]
    return {
        "validert": all(checks),
        "detaljer": (
            f"SymPy satte løsningen inn i likningen og evaluerte residualene "
            f"med evalf i løsningspunktene {supplied_values}. "
            f"Tre tilfeldige testpunkter var {points}, men brukes ikke som røtter. "
            f"Toleranse: {TOLERANSE}; residualer: {residuals}; resultater: {checks}."
        ),
    }


def validate(problem: str, losning: str) -> dict[str, Any]:
    """Valider en tekstlig løsning og returner tydelig status ved usikkerhet."""
    if not problem.strip() or not losning.strip():
        return {"validert": False, "detaljer": "Både problem og løsning må oppgis."}
    try:
        lowered = problem.lower()
        variable = "x"
        if "deriver" in lowered or "differentier" in lowered or "derivér" in lowered:
            return _validate_derivative(problem, losning, variable)
        if "=" in problem and not any(marker in lowered for marker in ("differensial", "ode", "dy/dx", "y'")):
            return _validate_equation(problem, losning, variable)
        return {
            "validert": False,
            "detaljer": (
                "Validering var ikke mulig: denne oppgavetypen kan ikke kontrolleres "
                "som en funksjonslikhet eller algebraisk likning med den tilgjengelige "
                "SymPy-parseren. Ingen verifisering påstås."
            ),
        }
    except Exception as error:
        return {"validert": False, "detaljer": f"Kunne ikke validere løsningen: {error}"}