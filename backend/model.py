"""Valgfri språkmodell for forklaring, aldri for selve beregningen."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parent.parent


def _api_key() -> str | None:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "OPENROUTER_API_KEY":
                return value.strip().strip('"\'')
    return None


def explain(
    problem: str,
    result: str,
    steps: list[dict[str, object]],
    formulas: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Be modellen forklare allerede beregnede fakta, uten å regne selv."""
    if os.getenv("OPENROUTER_ENABLE", "false").lower() not in {"1", "true", "yes"}:
        return {"brukt": False, "status": "avslått", "tekst": "Lokal SymPy-forklaring er brukt. Sett OPENROUTER_ENABLE=true for språkmodellforklaring."}
    api_key = _api_key()
    if not api_key:
        return {"brukt": False, "status": "ikke konfigurert", "tekst": "Lokal SymPy-forklaring er brukt."}

    body = {
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du er en pedagogisk matematikkforklarer. Ikke gjør eller endre beregninger. "
                    "Forklar kun de ferdig beregnede stegene og resultatet du får oppgitt. "
                    "Hvis noe ikke kan bekreftes av de oppgitte faktaene, si det tydelig."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "oppgave": problem,
                        "resultat": result,
                        "steg": steps,
                        "formelsamling": formulas or [],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
    }
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:8000"),
            "X-Title": os.getenv("SITE_NAME", "Mattehjelpen"),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
        return {"brukt": True, "status": "ok", "modell": body["model"], "tekst": text}
    except Exception as error:
        return {
            "brukt": False,
            "status": "feil ved forklaringskall",
            "tekst": "Lokal SymPy-forklaring er brukt.",
            "feil": str(error),
        }
