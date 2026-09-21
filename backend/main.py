"""FastAPI-applikasjon for Mattehjelpen."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import tools
from . import llm_client, validator
from .model import explain


class ExpressionRequest(BaseModel):
    """Body for derivasjon og integrasjon."""

    expression: str = Field(description="Matematisk uttrykk, for eksempel x^2 + 3*x.")
    variable: str = Field(default="x", description="Variabel som skal brukes.")


class EquationRequest(BaseModel):
    """Body for algebraiske likninger."""

    equation: str = Field(description="Likning, for eksempel x^2 - 4 = 0.")
    variable: str = Field(default="x", description="Variabel som skal løses.")


class SystemRequest(BaseModel):
    """Body for likningssett."""

    equations: list[str] = Field(description="Likningene i likningssettet.")
    variables: list[str] = Field(description="Variablene som skal løses.")


class OdeRequest(BaseModel):
    """Body for ordinære differensiallikninger."""

    equation: str = Field(description="Differensiallikning, for eksempel y' = y.")
    function: str = Field(default="y", description="Navn på den avhengige funksjonen.")
    variable: str = Field(default="x", description="Uavhengig variabel.")


class MatrixRequest(BaseModel):
    """Body for matriseoperasjoner."""

    operation: str = Field(description="add, subtract, multiply, determinant, inverse eller transpose.")
    matrix_a: list[list[Any]] = Field(description="Første matrise.")
    matrix_b: list[list[Any]] | None = Field(default=None, description="Andre matrise ved add, subtract eller multiply.")


class ComplexRequest(BaseModel):
    """Body for operasjoner på komplekse tall."""

    operation: str = Field(description="add, subtract, multiply, divide, conjugate, abs eller arg.")
    number_a: str = Field(description="Første komplekse tall, for eksempel 2 + 3*I.")
    number_b: str | None = Field(default=None, description="Andre tall ved add, subtract, multiply eller divide.")


class PythagorasRequest(BaseModel):
    """Body for Pytagoras."""

    side_a: float | None = Field(default=None, description="Katet a.")
    side_b: float | None = Field(default=None, description="Katet b.")
    hypotenuse: float | None = Field(default=None, description="Hypotenusen c.")


class SolveRequest(BaseModel):
    """Generisk oppgave til hovedløseren."""

    oppgave: str | None = Field(default=None, description="Oppgave som skal løses.")
    problem: str | None = Field(default=None, description="Bakoverkompatibelt navn for oppgave.")
    variable: str = Field(default="x", description="Variabel som brukes i oppgaven.")


ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT_DIR / "index.html"

app = FastAPI(title="Mattehjelpen API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Serverer appens frontend på samme origin som API-et."""
    return FileResponse(INDEX_FILE)


@app.get("/index.html", include_in_schema=False)
def index_html() -> FileResponse:
    """Serverer startfilen for frontend."""
    return FileResponse(INDEX_FILE)


@app.get("/app.js", include_in_schema=False)
def app_js() -> FileResponse:
    """Serverer frontend-JS."""
    return FileResponse(ROOT_DIR / "app.js")


@app.get("/styles.css", include_in_schema=False)
def styles_css() -> FileResponse:
    """Serverer frontend-CSS."""
    return FileResponse(ROOT_DIR / "styles.css")


@app.get("/health")
def health() -> dict[str, str]:
    """Bekrefter at API-et kjører."""
    return {"status": "ok"}


@app.post("/tools/derive")
def derive(payload: ExpressionRequest) -> dict[str, str]:
    """Deriverer et uttrykk."""
    return tools.derive(payload.expression, payload.variable)


@app.post("/tools/integrate")
def integrate(payload: ExpressionRequest) -> dict[str, str]:
    """Integrerer et uttrykk."""
    return tools.integrate(payload.expression, payload.variable)


@app.post("/tools/solve_equation")
def solve_equation(payload: EquationRequest) -> dict[str, str]:
    """Løser en algebraisk likning."""
    return tools.solve_equation(payload.equation, payload.variable)


@app.post("/tools/solve_system")
def solve_system(payload: SystemRequest) -> dict[str, str]:
    """Løser et likningssett."""
    return tools.solve_system(payload.equations, payload.variables)


@app.post("/tools/solve_ode")
def solve_ode(payload: OdeRequest) -> dict[str, str]:
    """Løser en ordinær differensiallikning."""
    return tools.solve_ode(payload.equation, payload.function, payload.variable)


@app.post("/tools/matrix_op")
def matrix_op(payload: MatrixRequest) -> dict[str, str]:
    """Utfører en matriseoperasjon."""
    return tools.matrix_op(payload.operation, payload.matrix_a, payload.matrix_b)


@app.post("/tools/complex_op")
def complex_op(payload: ComplexRequest) -> dict[str, str]:
    """Utfører en operasjon på komplekse tall."""
    return tools.complex_op(payload.operation, payload.number_a, payload.number_b)


@app.post("/tools/pythagoras")
def pythagoras(payload: PythagorasRequest) -> dict[str, str]:
    """Finner en ukjent side i en rettvinklet trekant."""
    return tools.pythagoras(payload.side_a, payload.side_b, payload.hypotenuse)


@app.post("/solve")
def solve(payload: SolveRequest) -> dict[str, Any]:
    """Løser en oppgave med LLM, faktiske SymPy-verktøykall og validator."""
    problem = payload.oppgave or payload.problem
    if not problem or not problem.strip():
        raise HTTPException(status_code=422, detail="Feltet 'oppgave' må inneholde en oppgave.")
    try:
        llm_result = llm_client.solve_task(problem)
        validation = validator.validate(problem, llm_result["svar"])
        return {
            "svar": llm_result["svar"],
            "steg": llm_result.get("steg", []),
            "formler_brukt": llm_result.get("formler_brukt", []),
            "validert": validation["validert"],
            "tokens_brukt": llm_result.get("tokens_brukt", 0),
            "estimert_kostnad": llm_result.get("estimert_kostnad", 0.0),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Kunne ikke behandle oppgaven ærlig: {error}") from error