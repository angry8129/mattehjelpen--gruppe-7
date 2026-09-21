"""Klient for OpenAI-kompatible API-er med SymPy-verktøykall."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from . import tools
from .explanations import FORMULAS


load_dotenv()
USE_TOOLS = os.getenv("USE_TOOLS", "true").lower() in {"1", "true", "yes"}
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "8"))

SYSTEMPROMPT = """Du er en matematikklærer for ingeniørstudenter. Bruk verktøyene (SymPy) til all beregning når oppgaven lar seg beregne slik – du skal ALDRI late som du har brukt et verktøy du ikke faktisk kalte. Kan oppgaven ikke beregnes (f.eks. et bevis eller en begrepsforklaring), resonnerer du i tekst og sier eksplisitt at svaret IKKE er verifisert av et verktøy. Forklar hvert steg pedagogisk på norsk, og oppgi nøyaktig hvilke formler/verktøy du faktisk brukte, med referanse til formelsamlingen. Hvis du er usikker, si det eksplisitt.

Svar som JSON med feltene svar (tekst), steg (liste med strenger) og formler_brukt (liste med formel-ID-er). Knytt hver formel-ID til steget der den brukes, og bruk bare ID-er fra formelsamlingen."""


def _catalog() -> list[dict[str, str]]:
    return [formula.__dict__ for formula in FORMULAS.values()]


def _usage(usages: list[Any]) -> tuple[int, float]:
    prompt = sum(int(getattr(item, "prompt_tokens", 0) or 0) for item in usages)
    completion = sum(int(getattr(item, "completion_tokens", 0) or 0) for item in usages)
    input_rate = float(os.getenv("INPUT_COST_PER_MILLION", "0"))
    output_rate = float(os.getenv("OUTPUT_COST_PER_MILLION", "0"))
    return prompt + completion, (prompt * input_rate + completion * output_rate) / 1_000_000


def _arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "derive": {"expression": "expression", "uttrykk": "expression", "variable": "variable", "variabel": "variable"},
        "integrate": {"expression": "expression", "uttrykk": "expression", "variable": "variable", "variabel": "variable"},
        "solve_equation": {"equation": "equation", "ligning": "equation", "variable": "variable", "variabel": "variable"},
        "solve_ode": {"equation": "equation", "ligning": "equation", "function": "function", "variable": "variable"},
        "matrix_op": {"operation": "operation", "matrix_a": "matrix_a", "matrix_b": "matrix_b"},
        "complex_op": {"operation": "operation", "number_a": "number_a", "number_b": "number_b"},
    }
    return {target: arguments[source] for source, target in aliases.get(name, {}).items() if source in arguments}


def _final(content: str | None) -> dict[str, Any]:
    if not content:
        return {"svar": "Modellen returnerte ingen tekst.", "steg": [], "formler_brukt": []}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"svar": content, "steg": [], "formler_brukt": []}
    return {
        "svar": str(parsed.get("svar", "")),
        "steg": [str(step) for step in parsed.get("steg", [])],
        "formler_brukt": list(parsed.get("formler_brukt", [])),
    }


def _validated_formulas(ids: list[Any]) -> list[dict[str, str]]:
    by_id = {formula.formula_id: formula.__dict__ for formula in FORMULAS.values()}
    unknown = [str(item) for item in ids if str(item) not in by_id]
    if unknown:
        raise ValueError(f"Ukjente formel-ID-er fra modellen: {', '.join(unknown)}")
    return [by_id[str(item)] for item in ids]


def solve_task(oppgave: str) -> dict[str, Any]:
    """Kjør modellen til den svarer, eller til maks antall tool-runder er nådd."""
    api_key = os.getenv("API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY eller OPENROUTER_API_KEY mangler i .env.")
    client = OpenAI(api_key=api_key, base_url=os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1"))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEMPROMPT},
        {"role": "system", "content": "FORMELSAMLING: " + json.dumps(_catalog(), ensure_ascii=False, separators=(",", ":"))},
        {"role": "user", "content": oppgave},
    ]
    usages: list[Any] = []
    tool_log: list[dict[str, Any]] = []
    functions = {
        "derive": tools.derive,
        "integrate": tools.integrate,
        "solve_equation": tools.solve_equation,
        "solve_ode": tools.solve_ode,
        "matrix_op": tools.matrix_op,
        "complex_op": tools.complex_op,
    }

    for _ in range(MAX_TOOL_ROUNDS):
        request: dict[str, Any] = {
            "model": os.getenv("MODEL_NAME", os.getenv("OPENROUTER_MODEL", "openrouter/free")),
            "messages": messages,
            "temperature": 0,
        }
        if USE_TOOLS:
            request["tools"] = tools.TOOL_DEFINITIONS
            request["tool_choice"] = "auto"
        response = client.chat.completions.create(**request)
        if response.usage:
            usages.append(response.usage)
        message = response.choices[0].message
        if not message.tool_calls:
            result = _final(message.content)
            result["formler_brukt"] = _validated_formulas(result["formler_brukt"])
            result["tokens_brukt"], result["estimert_kostnad"] = _usage(usages)
            result["tool_log"] = tool_log
            return result
        messages.append({"role": "assistant", "content": message.content, "tool_calls": [call.model_dump() for call in message.tool_calls]})
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            function = functions.get(call.function.name)
            if function is None:
                tool_result = {"feil": f"Ukjent verktøy: {call.function.name}"}
            else:
                try:
                    tool_result = function(**_arguments(call.function.name, arguments))
                except Exception as error:
                    tool_result = {"feil": str(error)}
            tool_log.append({"id": call.id, "navn": call.function.name, "argumenter": arguments, "resultat": tool_result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(tool_result, ensure_ascii=False)})
    raise RuntimeError(f"Maksgrensen på {MAX_TOOL_ROUNDS} tool-runder ble nådd.")