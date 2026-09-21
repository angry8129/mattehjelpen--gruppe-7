"""Strukturerte forklaringer, formelreferanser og validering for matematikksvar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp


@dataclass(frozen=True)
class Formula:
    formula_id: str
    name: str
    expression: str
    reference: str
    use: str = ""


FORMULAS: dict[str, Formula] = {
    "derivative": Formula(
        "DER-001",
        "Derivasjon av potens",
        "d/dx(x^n) = n*x^(n-1)",
        "Jarle Johannessen, Tekniske tabeller, kap. Derivasjon",
    ),
    "product_rule": Formula(
        "DER-002",
        "Produktregelen",
        "(f*g)' = f'*g + f*g'",
        "Jarle Johannessen, Tekniske tabeller, kap. Derivasjon",
    ),
    "chain_rule": Formula(
        "D2",
        "Kjerneregelen",
        "(f(g(x)))' = f'(g(x))*g'(x)",
        "Thomas' Calculus, kap. 3",
        "Når en sammensatt funksjon skal deriveres.",
    ),
    "partial_integration": Formula(
        "I1",
        "Delvis integrasjon",
        r"\int u\,dv = uv - \int v\,du",
        "Thomas' Calculus, kap. 8",
        "Når integralet inneholder et produkt som blir enklere etter derivasjon av én faktor.",
    ),
    "characteristic_equation": Formula(
        "O1",
        "Karakteristisk ligning (2. ordens lineær ODE)",
        r"ar^2 + br + c = 0 \text{ for } ay'' + by' + cy = 0",
        "Edwards & Penney, kap. 3",
        "Når en homogen lineær differensiallikning med konstante koeffisienter skal løses.",
    ),
    "euler_formula": Formula(
        "K1",
        "Eulers formel",
        r"e^{i\theta} = \cos\theta + i\sin\theta",
        "Buanes: Komplekse tall",
        "Når komplekse tall skal kobles mellom eksponentialform og trigonometrisk form.",
    ),
    "determinant_2x2": Formula(
        "M1",
        "Determinant (2x2)",
        r"\det\begin{pmatrix}a & b\\ c & d\end{pmatrix} = ad - bc",
        "Edwards & Penney, kap. 4",
        "Når determinanten til en 2x2-matrise skal beregnes eller inverterbarhet vurderes.",
    ),
    "integral": Formula(
        "INT-001",
        "Potensregelen for integrasjon",
        "integral(x^n dx) = x^(n+1)/(n+1) + C",
        "Jarle Johannessen, Tekniske tabeller, kap. Integrasjon",
    ),
    "linear_ode": Formula(
        "ODE-001",
        "Lineær førsteordens differensiallikning",
        "y' + p(x)y = q(x), mu(x) = exp(integral(p(x) dx))",
        "Jarle Johannessen, Tekniske tabeller, kap. Differensiallikninger",
    ),
    "pythagoras": Formula(
        "GEO-001",
        "Pythagoras' læresetning",
        "a^2 + b^2 = c^2",
        "Jarle Johannessen, Tekniske tabeller, kap. Geometri",
    ),
    "equation": Formula(
        "ALG-001",
        "Likningsregel",
        "Hvis a = b, kan samme algebraiske operasjon utføres på begge sider",
        "Jarle Johannessen, Tekniske tabeller, kap. Algebra",
    ),
}


def formula_payload(keys: list[str]) -> list[dict[str, str]]:
    return [FORMULAS[key].__dict__ for key in keys if key in FORMULAS]


def success_payload(
    *,
    result: Any,
    latex: str,
    steps: list[dict[str, Any]],
    formulas: list[str],
    validation: dict[str, Any],
    explanation: str,
    model_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "resultat": str(result),
        "latex": latex,
        "steg": steps,
        "formler": formula_payload(formulas),
        "validering": validation,
        "forklaring": explanation,
        "verifisert_av_verktøy": bool(validation.get("verifisert")),
    }
    if model_info:
        payload["sprakmodell"] = model_info
    return payload


def verified(label: str, details: str) -> dict[str, Any]:
    return {"verifisert": True, "type": "sympy", "beskrivelse": label, "detaljer": details}


def unverified(label: str, details: str) -> dict[str, Any]:
    return {"verifisert": False, "type": "tekstresonnement", "beskrivelse": label, "detaljer": details}


def proof_response(problem: str) -> dict[str, Any]:
    return success_payload(
        result="Tekstbevis kreves",
        latex="",
        steps=[
            {"nummer": 1, "tekst": "Dette er en bevis-/begrepsoppgave, ikke en direkte symbolsk beregning."},
            {"nummer": 2, "tekst": "Oppgaven må besvares med et matematisk resonnement i tekst."},
        ],
        formulas=[],
        validation=unverified(
            "Ikke verifisert av SymPy",
            "Appen har ikke en deterministisk beviskontroll for denne oppgavetypen.",
        ),
        explanation=(
            f"Oppgaven «{problem}» behandles som et tekstbevis. "
            "Svaret må vurderes faglig; appen påstår ikke at et språkmodell-svar er verifisert."
        ),
    )


def derivative_steps(expression: sp.Expr, variable: sp.Symbol, value: sp.Expr) -> list[dict[str, Any]]:
    return [
        {"nummer": 1, "tekst": f"Uttrykket tolkes som f(x) = {expression}."},
        {"nummer": 2, "tekst": f"Deriver med hensyn på {variable} ved hjelp av produkt-, potens- og/eller kjerneregelen."},
        {"nummer": 3, "tekst": f"SymPy forenkler den deriverte til {value}."},
    ]


def validation_for_expression(original: sp.Expr, result: sp.Expr, variable: sp.Symbol) -> dict[str, Any]:
    return verified(
        "Derivert uttrykk kontrollert symbolsk",
        f"SymPy beregnet diff({original}, {variable}) = {result}.",
    )


def validate_equation(equation: sp.Eq, solution: Any, variable: sp.Symbol) -> dict[str, Any]:
    residuals = []
    values = solution if isinstance(solution, list) else [solution]
    for value in values:
        residuals.append(sp.simplify(equation.lhs.subs(variable, value) - equation.rhs.subs(variable, value)))
    passed = all(residual == 0 for residual in residuals)
    return {
        "verifisert": passed,
        "type": "sympy",
        "beskrivelse": "Løsningen satt inn i likningen",
        "detaljer": f"Residualer: {residuals}",
    }


def validate_system(equations: list[sp.Eq], solution: dict[sp.Symbol, Any]) -> dict[str, Any]:
    residuals = [sp.simplify(eq.lhs.subs(solution) - eq.rhs.subs(solution)) for eq in equations]
    passed = all(residual == 0 for residual in residuals)
    return {
        "verifisert": passed,
        "type": "sympy",
        "beskrivelse": "Løsningen satt inn i alle likningene",
        "detaljer": f"Residualer: {residuals}",
    }
