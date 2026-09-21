# Mattehjelpen

Dette prosjektet inneholder en liten FastAPI-server med matematiske verktøy og en egen generisk solve-post.

## Start appen

```bash
cd /workspaces/mattehjelpen--gruppe-7
python run_server.py
```

Serveren starter på:

```text
http://localhost:8000
```

Swagger-dokumentasjonen ligger på:

```text
http://localhost:8000/docs
```

## Endepunkter

### 1. Generisk solve-post

```http
POST /solve
```

Brukes for å løse en oppgave på vanlig språk eller med et uttrykk.

Eksempel:

```json
{
  "problem": "deriver x^2 + 3*x - 1",
  "variable": "x"
}
```

Responsen inneholder også stegvis forklaring, formelreferanser og validering:

```json
{
  "resultat": "2*x + 3",
  "latex": "2 x + 3",
  "steg": [],
  "formler": [],
  "validering": {
    "verifisert": true,
    "type": "sympy"
  },
  "verifisert_av_verktøy": true
}
```

Støttede oppgaveformer:
- "deriver ..."
- "integrer ..."
- "løs ..."
- likninger som inneholder "="
- enkel differensiallikningstekst
- bevis-/begrepsoppgaver markeres som tekstresonnement og ikke verifisert av SymPy

Alle symbolske og numeriske beregninger i `/solve` utføres deterministisk med SymPy.
En valgfri OpenRouter-modell kan formulere forklaringen, men får kun beregnede steg og
resultater som input og er aldri autoritet for fasiten. For å aktivere den, legg inn
`OPENROUTER_API_KEY` i `.env` og sett `OPENROUTER_ENABLE=true`. Uten dette brukes lokal
forklaring uten nettverkskall.

Formelreferansene ligger i `backend/explanations.py` og har ID, navn, formel og
referanse til innebygd tabellsamling. Oppdater referanseteksten der dersom prosjektet
skal bruke en bestemt utgave eller kapittelinndeling av formelsamlingen.

### 2. Derivasjon

```http
POST /tools/derive
```

Body:

```json
{
  "expression": "x^2 + 3*x - 1",
  "variable": "x"
}
```

### 3. Integrasjon

```http
POST /tools/integrate
```

Body:

```json
{
  "expression": "x^2 + 3*x - 1",
  "variable": "x"
}
```

### 4. Løs likning

```http
POST /tools/solve_equation
```

Body:

```json
{
  "equation": "x^2 - 4 = 0",
  "variable": "x"
}
```

### 5. Løs differensiallikning

```http
POST /tools/solve_ode
```

Body:

```json
{
  "equation": "y' = y",
  "function": "y",
  "variable": "x"
}
```

### 6. Løs likningssett

```http
POST /tools/solve_system
```

Body:

```json
{
  "equations": [
    "2*x + 3*y = 7",
    "x - y = 1"
  ],
  "variables": ["x", "y"]
}
```

Du kan også bruke `/solve`:

```json
{
  "problem": "løs likningssett: 2*x + 3*y = 7; x - y = 1",
  "variable": "x,y"
}
```

### 7. Matriseoperasjoner

```http
POST /tools/matrix_op
```

Body:

```json
{
  "operation": "multiply",
  "matrix_a": [[1, 2], [3, 4]],
  "matrix_b": [[5, 6], [7, 8]]
}
```

### 8. Komplekse tall

```http
POST /tools/complex_op
```

Body:

```json
{
  "operation": "add",
  "number_a": "2 + 3*I",
  "number_b": "1 - 2*I"
}
```

### 9. Pytagoras

```http
POST /tools/pythagoras
```

Oppgi nøyaktig to av sidene:

```json
{
  "side_a": 3,
  "side_b": 4
}
```

Dette gir `hypotenuse = 5`. Du kan også bruke `/solve`:

```json
{
  "problem": "pytagoras a=3, b=4",
  "variable": "x"
}
```

## Tips

- Bruk `*` for multiplikasjon: `3*x`
- Bruk `^` for eksponenter: `x^2`
- Variabelen er som standard `x`
- Den generiske `/solve`-posten er best for enkelt oppgaver uten at du trenger å velge tool manuelt
