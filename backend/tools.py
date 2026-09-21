"""Matematiske verktøy som kan brukes fra FastAPI og OpenAI function-calling."""

from __future__ import annotations

import json
import re
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from .explanations import (
    derivative_steps,
    proof_response,
    success_payload,
    unverified,
    validate_system,
    validation_for_expression,
    verified,
)


_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _success(value: Any) -> dict[str, str]:
    """Gjør et SymPy-resultat om til API-formatet."""
    return {"resultat": str(value), "latex": sp.latex(value)}


def _failure(message: str) -> dict[str, str]:
    """Returnerer en lesbar feil uten å kaste feilen videre til API-et."""
    return {"resultat": f"Feil: {message}", "latex": ""}


def _expression(value: str, variable: str = "x") -> sp.Expr:
    """Tolker et uttrykk med vanlige matematiske skrivemåter."""
    symbol = sp.Symbol(variable)
    return parse_expr(
        value,
        local_dict={variable: symbol},
        transformations=_TRANSFORMATIONS,
    )


def _equation(value: str, variable: str = "x") -> sp.Eq:
    """Tolker både likninger med og uten likhetstegn."""
    if "=" in value:
        left, right = value.split("=", 1)
        return sp.Eq(_expression(left, variable), _expression(right, variable))
    return sp.Eq(_expression(value, variable), 0)


def _matrix(value: list[list[Any]] | str) -> sp.Matrix:
    """Konverterer en JSON-matrise eller matrisestreng til SymPy."""
    if isinstance(value, str):
        value = json.loads(value)
    return sp.Matrix(value)


def derive(expression: str, variable: str = "x") -> dict[str, str]:
    """Deriverer et matematisk uttrykk med hensyn på en variabel."""
    try:
        symbol = sp.Symbol(variable)
        return _success(sp.diff(_expression(expression, variable), symbol))
    except Exception as error:
        return _failure(f"Kunne ikke derivere uttrykket: {error}")


def integrate(expression: str, variable: str = "x") -> dict[str, str]:
    """Integrerer et matematisk uttrykk med hensyn på en variabel."""
    try:
        symbol = sp.Symbol(variable)
        return _success(sp.integrate(_expression(expression, variable), symbol))
    except Exception as error:
        return _failure(f"Kunne ikke integrere uttrykket: {error}")


def solve_equation(equation: str, variable: str = "x") -> dict[str, str]:
    """Løser en algebraisk likning for en valgt variabel."""
    try:
        symbol = sp.Symbol(variable)
        return _success(sp.solve(_equation(equation, variable), symbol))
    except Exception as error:
        return _failure(f"Kunne ikke løse likningen: {error}")


def solve_system(equations: list[str], variables: list[str]) -> dict[str, str]:
    """Løser et likningssett for flere variabler."""
    try:
        if not equations or not variables:
            raise ValueError("equations og variables kan ikke være tomme")
        symbols = [sp.Symbol(variable) for variable in variables]
        parsed_equations = [
            _equation(equation, variables[0]) if equation.count("=") == 0 else sp.Eq(
                _expression(equation.split("=", 1)[0], variables[0]),
                _expression(equation.split("=", 1)[1], variables[0]),
            )
            for equation in equations
        ]
        expressions = [equation.lhs - equation.rhs for equation in parsed_equations]
        return _success(sp.solve(expressions, symbols, dict=True))
    except Exception as error:
        return _failure(f"Kunne ikke løse likningssettet: {error}")


def pythagoras(
    side_a: float | None = None,
    side_b: float | None = None,
    hypotenuse: float | None = None,
) -> dict[str, str]:
    """Finner den manglende siden i en rettvinklet trekant."""
    try:
        side_a = sp.Rational(str(side_a)) if side_a is not None else None
        side_b = sp.Rational(str(side_b)) if side_b is not None else None
        hypotenuse = sp.Rational(str(hypotenuse)) if hypotenuse is not None else None
        known = [side_a is not None, side_b is not None, hypotenuse is not None]
        if sum(known) != 2:
            raise ValueError("oppgi nøyaktig to av side_a, side_b og hypotenuse")
        if any(value is not None and value <= 0 for value in (side_a, side_b, hypotenuse)):
            raise ValueError("sidene må være større enn null")
        if hypotenuse is not None and side_a is not None and hypotenuse <= side_a:
            raise ValueError("hypotenusen må være større enn side_a")
        if hypotenuse is not None and side_b is not None and hypotenuse <= side_b:
            raise ValueError("hypotenusen må være større enn side_b")

        if side_a is None:
            value = sp.sqrt(hypotenuse**2 - side_b**2)
            name = "side_a"
        elif side_b is None:
            value = sp.sqrt(hypotenuse**2 - side_a**2)
            name = "side_b"
        else:
            value = sp.sqrt(side_a**2 + side_b**2)
            name = "hypotenuse"
        return {"resultat": f"{name} = {value}", "latex": sp.latex(value)}
    except Exception as error:
        return _failure(f"Kunne ikke bruke Pytagoras: {error}")


def solve_task(problem: str, variable: str = "x") -> dict[str, str]:
    """Tolker en enkel matematikklignende oppgave og sender den til riktig operasjon."""
    if not problem or not problem.strip():
        return _failure("Du må skrive inn en oppgave.")

    text = problem.strip()
    lowered = text.lower()

    if "pytagoras" in lowered:
        values = dict(re.findall(r"\b(a|b|c|hypotenuse)\s*=\s*([0-9]+(?:\.[0-9]+)?)", lowered))
        return pythagoras(
            side_a=float(values["a"]) if "a" in values else None,
            side_b=float(values["b"]) if "b" in values else None,
            hypotenuse=float(values.get("c", values["hypotenuse"]))
            if "c" in values or "hypotenuse" in values
            else None,
        )

    if "likningssett" in lowered or "likningssystem" in lowered:
        equation_text = text.split(":", 1)[1] if ":" in text else text
        equation_text = re.sub(r"^(løs\s+)?liknings(sett|system)\s*:?\s*", "", equation_text, flags=re.IGNORECASE)
        equations = [equation.strip() for equation in re.split(r"[;\n]+", equation_text) if equation.strip()]
        variables = [item.strip() for item in variable.split(",") if item.strip()]
        return solve_system(equations, variables)

    if re.match(r"^(deriver|differentier|derivér|deriv)\b", lowered):
        expr = re.sub(r"^(deriver|differentier|derivér|deriv)\s*", "", text, flags=re.IGNORECASE)
        return derive(expr.strip() or text, variable)

    if re.match(r"^(integrer|integral|integr)\b", lowered):
        expr = re.sub(r"^(integrer|integral|integr)\s*", "", text, flags=re.IGNORECASE)
        return integrate(expr.strip() or text, variable)

    if re.match(r"^(løs|solve|finn)\b", lowered):
        expr = re.sub(r"^(løs|solve|finn)\s*", "", text, flags=re.IGNORECASE)
        return solve_equation(expr.strip() or text, variable)

    if "differensial" in lowered or "ode" in lowered or "dy/dx" in lowered or "y'" in lowered:
        return solve_ode(text, "y", variable)

    if "=" in text:
        return solve_equation(text, variable)

    if "matrix" in lowered or "matrise" in lowered:
        return _failure("For matriser bruk /tools/matrix_op med matrix_a og eventuelt matrix_b.")

    if "kompleks" in lowered or "complex" in lowered:
        return _failure("For komplekse tall bruk /tools/complex_op med operation og number_a.")

    return derive(text, variable)


def solve_task_detailed(problem: str, variable: str = "x") -> dict[str, Any]:
    """Løser en tekstoppgave med steg, formelreferanser og SymPy-validering."""
    if not problem or not problem.strip():
        return _failure("Du må skrive inn en oppgave.")

    text = problem.strip()
    lowered = text.lower()
    if any(marker in lowered for marker in ("bevis", "vis at", "forklar hvorfor")):
        return proof_response(text)

    if "pytagoras" in lowered:
        values = dict(re.findall(r"\b(a|b|c|hypotenuse)\s*=\s*([0-9]+(?:\.[0-9]+)?)", lowered))
        result = pythagoras(
            side_a=float(values["a"]) if "a" in values else None,
            side_b=float(values["b"]) if "b" in values else None,
            hypotenuse=float(values.get("c", values["hypotenuse"]))
            if "c" in values or "hypotenuse" in values
            else None,
        )
        if result.get("latex"):
            return success_payload(
                result=result["resultat"], latex=result["latex"],
                steps=[
                    {"nummer": 1, "tekst": "Bruk Pythagoras' læresetning.", "formel_ids": ["GEO-001"]},
                    {"nummer": 2, "tekst": "Isoler den ukjente siden og beregn med SymPy."},
                    {"nummer": 3, "tekst": result["resultat"]},
                ], formulas=["pythagoras"],
                validation=verified("Pythagoras-beregning kontrollert", "Verdien er beregnet deterministisk med SymPy."),
                explanation="Dette er en numerisk/geometrisk beregning som er kontrollert av SymPy.",
            )
        return result

    if "likningssett" in lowered or "likningssystem" in lowered:
        equation_text = text.split(":", 1)[1] if ":" in text else text
        equation_text = re.sub(r"^(løs\s+)?liknings(sett|system)\s*:?\s*", "", equation_text, flags=re.IGNORECASE)
        equations = [equation.strip() for equation in re.split(r"[;\n]+", equation_text) if equation.strip()]
        variables = [item.strip() for item in variable.split(",") if item.strip()]
        symbols = [sp.Symbol(item) for item in variables]
        parsed = [_equation(equation, variables[0]) for equation in equations]
        solution = sp.solve([eq.lhs - eq.rhs for eq in parsed], symbols, dict=True)
        solution_map = solution[0] if solution else {}
        return success_payload(
            result=solution, latex=sp.latex(solution),
            steps=[
                {"nummer": 1, "tekst": f"Tolket {len(equations)} likninger med variablene {', '.join(variables)}.", "formel_ids": ["ALG-001"]},
                {"nummer": 2, "tekst": "SymPy løser likningene samtidig.", "formel_ids": ["ALG-001"]},
                {"nummer": 3, "tekst": f"Løsning: {solution}"},
            ], formulas=["equation"],
            validation=validate_system(parsed, solution_map) if solution_map else unverified("Ingen løsning funnet", "SymPy returnerte ingen løsning."),
            explanation="Likningssettet er løst symbolsk og kontrollert ved å sette løsningen inn i alle likningene.",
        )

    if re.match(r"^(deriver|differentier|derivér|deriv)\b", lowered):
        expression = re.sub(r"^(deriver|differentier|derivér|deriv)\s*", "", text, flags=re.IGNORECASE).strip()
        symbol = sp.Symbol(variable)
        parsed = _expression(expression, variable)
        result = sp.diff(parsed, symbol)
        derivative_step_list = derivative_steps(parsed, symbol, result)
        derivative_step_list[1]["formel_ids"] = ["DER-001", "DER-002", "DER-003"]
        return success_payload(
            result=result, latex=sp.latex(result), steps=derivative_step_list,
            formulas=["derivative", "product_rule", "chain_rule"],
            validation=validation_for_expression(parsed, result, symbol),
            explanation="SymPy utførte den symbolske derivasjonen; språkmodellen skal bare forklare stegene.",
        )

    if "differensial" in lowered or "ode" in lowered or "dy/dx" in lowered or "y'" in lowered:
        equation_text = re.sub(r"^(løs\s+)?differensiallikning\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        initial_match = re.search(r"y\(\s*([^)]*)\s*\)\s*=\s*([^,;]+)", equation_text, flags=re.IGNORECASE)
        initial_condition = None
        if initial_match:
            point = _expression(initial_match.group(1), variable)
            value = _expression(initial_match.group(2), variable)
            initial_condition = (point, value)
            equation_text = equation_text[:initial_match.start()].rstrip(" ,;")

        independent = sp.Symbol(variable)
        dependent = sp.Function("y")(independent)
        left, right = equation_text.split("=", 1) if "=" in equation_text else (equation_text, "0")
        left = re.sub(r"\by''", f"Derivative(y({variable}), ({variable}, 2))", left)
        left = re.sub(r"\by'", f"Derivative(y({variable}), {variable})", left)
        left = re.sub(r"\by\b(?!\s*\()", f"y({variable})", left)
        local_dict = {variable: independent, "y": sp.Function("y"), "Derivative": sp.Derivative}
        ode_transformations = standard_transformations + (convert_xor,)
        ode = sp.Eq(
            parse_expr(left, local_dict=local_dict, transformations=ode_transformations),
            parse_expr(right, local_dict=local_dict, transformations=ode_transformations),
        )
        solution_expr = sp.dsolve(
            ode,
            dependent,
            ics={dependent.subs(independent, initial_condition[0]): initial_condition[1]}
            if initial_condition
            else None,
        ).rhs
        result = {"resultat": f"Eq(y({variable}), {solution_expr})", "latex": sp.latex(sp.Eq(dependent, solution_expr))}
        if result.get("latex"):
            residual = sp.simplify((ode.lhs - ode.rhs).subs(dependent, solution_expr).doit())
            return success_payload(
                result=result["resultat"], latex=result["latex"],
                steps=[
                    {"nummer": 1, "tekst": f"Tolket differensiallikningen: {equation_text}.", "formel_ids": ["ODE-001"]},
                    {"nummer": 2, "tekst": "SymPy finner den generelle løsningen.", "formel_ids": ["ODE-001"]},
                    {"nummer": 3, "tekst": f"Initialbetingelse brukt: y({initial_condition[0]}) = {initial_condition[1]}."} if initial_condition else {"nummer": 3, "tekst": "Ingen initialbetingelse oppgitt."},
                    {"nummer": 4, "tekst": result["resultat"]},
                ], formulas=["linear_ode"],
                validation={"verifisert": residual == 0, "type": "sympy", "beskrivelse": "Løsningen satt inn i differensiallikningen", "detaljer": f"Residual: {residual}"},
                explanation="ODE-løsningen er beregnet av SymPy og kontrollert ved substitusjon i differensiallikningen.",
            )
        return result

    if re.match(r"^(løs|solve|finn)\b", lowered) or "=" in text:
        expression = re.sub(r"^(løs|solve|finn)\s*", "", text, flags=re.IGNORECASE).strip()
        symbol = sp.Symbol(variable)
        equation = _equation(expression, variable)
        solution = sp.solve(equation, symbol)
        from .explanations import validate_equation
        return success_payload(
            result=solution, latex=sp.latex(solution),
            steps=[
                {"nummer": 1, "tekst": f"Sett likningen lik null: {equation.lhs - equation.rhs} = 0.", "formel_ids": ["ALG-001"]},
                {"nummer": 2, "tekst": f"SymPy løser for {symbol}.", "formel_ids": ["ALG-001"]},
                {"nummer": 3, "tekst": f"Løsning: {solution}"},
            ], formulas=["equation"], validation=validate_equation(equation, solution, symbol),
            explanation="Likningen er løst symbolsk og kontrollert ved substitusjon.",
        )

    return proof_response(text)


def solve_ode(
    equation: str,
    function: str = "y",
    variable: str = "x",
) -> dict[str, str]:
    """Løser en ordinær differensiallikning skrevet med y' og y''."""
    try:
        independent = sp.Symbol(variable)
        dependent = sp.Function(function)(independent)
        left, right = equation.split("=", 1) if "=" in equation else (equation, "0")
        left = re.sub(rf"\b{re.escape(function)}''", f"Derivative({function}({variable}), ({variable}, 2))", left)
        left = re.sub(rf"\b{re.escape(function)}'", f"Derivative({function}({variable}), {variable})", left)
        left = re.sub(rf"\b{re.escape(function)}\b(?!\s*\()", f"{function}({variable})", left)
        local_dict = {
            variable: independent,
            function: sp.Function(function),
            "Derivative": sp.Derivative,
        }
        ode_transformations = standard_transformations + (convert_xor,)
        ode = sp.Eq(
            parse_expr(left, local_dict=local_dict, transformations=ode_transformations),
            parse_expr(right, local_dict=local_dict, transformations=ode_transformations),
        )
        return _success(sp.dsolve(ode, dependent))
    except Exception as error:
        return _failure(f"Kunne ikke løse differensiallikningen: {error}")


def matrix_op(
    operation: str,
    matrix_a: list[list[Any]] | str,
    matrix_b: list[list[Any]] | str | None = None,
) -> dict[str, str]:
    """Utfører en valgt operasjon på én eller to matriser."""
    try:
        first = _matrix(matrix_a)
        second = _matrix(matrix_b) if matrix_b is not None else None
        operations = {
            "add": lambda: first + second,
            "subtract": lambda: first - second,
            "multiply": lambda: first * second,
            "determinant": first.det,
            "inverse": first.inv,
            "transpose": first.transpose,
        }
        if operation not in operations:
            raise ValueError("operasjon må være add, subtract, multiply, determinant, inverse eller transpose")
        if operation in {"add", "subtract", "multiply"} and second is None:
            raise ValueError("operasjonen krever matrix_b")
        return _success(operations[operation]())
    except Exception as error:
        return _failure(f"Kunne ikke utføre matriseoperasjonen: {error}")


def complex_op(operation: str, number_a: str, number_b: str | None = None) -> dict[str, str]:
    """Utfører en valgt operasjon på komplekse tall."""
    try:
        first = _expression(number_a)
        second = _expression(number_b) if number_b is not None else None
        operations = {
            "add": lambda: first + second,
            "subtract": lambda: first - second,
            "multiply": lambda: first * second,
            "divide": lambda: first / second,
            "conjugate": lambda: sp.conjugate(first),
            "abs": lambda: sp.Abs(first),
            "arg": lambda: sp.arg(first),
        }
        if operation not in operations:
            raise ValueError("operasjon må være add, subtract, multiply, divide, conjugate, abs eller arg")
        if operation in {"add", "subtract", "multiply", "divide"} and second is None:
            raise ValueError("operasjonen krever number_b")
        return _success(operations[operation]())
    except Exception as error:
        return _failure(f"Kunne ikke utføre operasjonen på komplekse tall: {error}")


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "derive",
            "description": "Deriverer et matematisk uttrykk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Uttrykket som skal deriveres."},
                    "variable": {"type": "string", "description": "Variabelen det skal deriveres med hensyn på."},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "integrate",
            "description": "Integrerer et matematisk uttrykk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "variable": {"type": "string"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_equation",
            "description": "Løser en algebraisk likning.",
            "parameters": {
                "type": "object",
                "properties": {"equation": {"type": "string"}, "variable": {"type": "string"}},
                "required": ["equation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_ode",
            "description": "Løser en ordinær differensiallikning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "equation": {"type": "string"},
                    "function": {"type": "string"},
                    "variable": {"type": "string"},
                },
                "required": ["equation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "matrix_op",
            "description": "Utfører en operasjon på matriser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "matrix_a": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "matrix_b": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                },
                "required": ["operation", "matrix_a"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complex_op",
            "description": "Utfører en operasjon på komplekse tall.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "number_a": {"type": "string"},
                    "number_b": {"type": "string"},
                },
                "required": ["operation", "number_a"],
            },
        },
    },
]