const operationSelect = document.getElementById('operation');
const fieldsContainer = document.getElementById('fields');
const resultBox = document.getElementById('result');
const runButton = document.getElementById('runButton');

function renderFields() {
  const operation = operationSelect.value;

  const fieldMap = {
    solve: `
      <div class="field-row">
        <label for="problem">Oppgave</label>
        <input id="problem" placeholder="deriver x^2 + 3*x - 1" />
      </div>
      <div class="field-row">
        <label for="variable">Variabel</label>
        <input id="variable" value="x" />
      </div>
    `,
    derive: `
      <div class="field-row">
        <label for="expression">Uttrykk</label>
        <input id="expression" value="x^2 + 3*x - 1" />
      </div>
      <div class="field-row">
        <label for="variable">Variabel</label>
        <input id="variable" value="x" />
      </div>
    `,
    integrate: `
      <div class="field-row">
        <label for="expression">Uttrykk</label>
        <input id="expression" value="x^2 + 3*x - 1" />
      </div>
      <div class="field-row">
        <label for="variable">Variabel</label>
        <input id="variable" value="x" />
      </div>
    `,
    solve_equation: `
      <div class="field-row">
        <label for="equation">Likning</label>
        <input id="equation" value="x^2 - 4 = 0" />
      </div>
      <div class="field-row">
        <label for="variable">Variabel</label>
        <input id="variable" value="x" />
      </div>
    `,
    solve_system: `
      <div class="field-row">
        <label for="equations">Likninger (én per linje)</label>
        <textarea id="equations">2*x + 3*y = 7
x - y = 1</textarea>
      </div>
      <div class="field-row">
        <label for="variables">Variabler</label>
        <input id="variables" value="x,y" />
      </div>
    `,
    solve_ode: `
      <div class="field-row">
        <label for="equation">Differensiallikning</label>
        <input id="equation" value="y' = y" />
      </div>
      <div class="field-row">
        <label for="function">Funksjon</label>
        <input id="function" value="y" />
      </div>
      <div class="field-row">
        <label for="variable">Variabel</label>
        <input id="variable" value="x" />
      </div>
    `,
    pythagoras: `
      <div class="field-row">
        <label for="sideA">side_a</label>
        <input id="sideA" value="3" />
      </div>
      <div class="field-row">
        <label for="sideB">side_b</label>
        <input id="sideB" value="4" />
      </div>
      <div class="field-row">
        <label for="hypotenuse">hypotenuse</label>
        <input id="hypotenuse" value="" placeholder="La stå tom hvis ukjent" />
      </div>
    `,
    matrix_op: `
      <div class="field-row">
        <label for="operationName">Operasjon</label>
        <input id="operationName" value="multiply" />
      </div>
      <div class="field-row">
        <label for="matrixA">Matrise A</label>
        <textarea id="matrixA">[[1,2],[3,4]]</textarea>
      </div>
      <div class="field-row">
        <label for="matrixB">Matrise B</label>
        <textarea id="matrixB">[[5,6],[7,8]]</textarea>
      </div>
    `,
    complex_op: `
      <div class="field-row">
        <label for="operationName">Operasjon</label>
        <input id="operationName" value="add" />
      </div>
      <div class="field-row">
        <label for="numberA">number_a</label>
        <input id="numberA" value="2 + 3*I" />
      </div>
      <div class="field-row">
        <label for="numberB">number_b</label>
        <input id="numberB" value="1 - 2*I" />
      </div>
    `,
  };

  fieldsContainer.innerHTML = fieldMap[operation] || fieldMap.solve;
}

operationSelect.addEventListener('change', renderFields);

function renderSolveResult(data) {
  const steps = (data.steg || [])
    .map((step, index) => typeof step === 'string'
      ? `${index + 1}. ${step}`
      : `${step.nummer}. ${step.tekst}${step.formel_ids?.length ? ` [${step.formel_ids.join(', ')}]` : ''}`)
    .join('\n');
  const formulas = (data.formler || [])
    .concat(data.formler_brukt || [])
    .map((formula) => `${formula.formula_id || formula.id}: ${formula.name || formula.navn}: ${formula.expression || formula.formel}\n  Referanse: ${formula.reference || formula.referanse}`)
    .join('\n');
  const validation = data.validering
    ? `${data.validering.verifisert ? 'VERIFISERT' : 'IKKE VERIFISERT'} (${data.validering.type})\n${data.validering.beskrivelse}\n${data.validering.detaljer}`
    : data.validert === undefined
      ? 'Ingen valideringsinformasjon.'
      : data.validert ? 'VERIFISERT' : 'IKKE VERIFISERT';
  const model = data.sprakmodell?.tekst ? `\n\nSpråkmodellens forklaring:\n${data.sprakmodell.tekst}` : '';

  resultBox.textContent = [
    `Svar: ${data.svar || data.resultat || ''}`,
    data.forklaring ? `\nForklaring:\n${data.forklaring}` : '',
    steps ? `\nStegvis løsning:\n${steps}` : '',
    formulas ? `\nFormler brukt:\n${formulas}` : '',
    `\nValidering:\n${validation}`,
    model,
  ].join('\n');
}

document.getElementById('reflectionButton').addEventListener('click', async () => {
  const example = {
    problem: 'deriver x^2 + 3*x - 1',
    variable: 'x',
  };

  resultBox.textContent = 'Eksempel fra refleksjonsnotatet:\n\n' + JSON.stringify(example, null, 2) + '\n\nSender til /solve...';

  try {
    const response = await fetch('/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(example),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail, null, 2) : 'Feil');
    }

    renderSolveResult(data);
  } catch (error) {
    resultBox.textContent = `Refleksjonsfunksjonen feilet:\n${error.message}`;
  }
});

runButton.addEventListener('click', async () => {
  const operation = operationSelect.value;
  let payload = {};
  let url = '';

  try {
    switch (operation) {
      case 'solve': {
        url = '/solve';
        payload = {
          problem: document.getElementById('problem').value,
          variable: document.getElementById('variable').value || 'x',
        };
        break;
      }
      case 'derive': {
        url = '/tools/derive';
        payload = {
          expression: document.getElementById('expression').value,
          variable: document.getElementById('variable').value || 'x',
        };
        break;
      }
      case 'integrate': {
        url = '/tools/integrate';
        payload = {
          expression: document.getElementById('expression').value,
          variable: document.getElementById('variable').value || 'x',
        };
        break;
      }
      case 'solve_equation': {
        url = '/tools/solve_equation';
        payload = {
          equation: document.getElementById('equation').value,
          variable: document.getElementById('variable').value || 'x',
        };
        break;
      }
      case 'solve_system': {
        url = '/tools/solve_system';
        const eqValue = document.getElementById('equations').value;
        payload = {
          equations: eqValue.split(/\n|;/).map((eq) => eq.trim()).filter(Boolean),
          variables: (document.getElementById('variables').value || 'x,y')
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
        };
        break;
      }
      case 'solve_ode': {
        url = '/tools/solve_ode';
        payload = {
          equation: document.getElementById('equation').value,
          function: document.getElementById('function').value || 'y',
          variable: document.getElementById('variable').value || 'x',
        };
        break;
      }
      case 'pythagoras': {
        url = '/tools/pythagoras';
        payload = {
          side_a: document.getElementById('sideA').value ? Number(document.getElementById('sideA').value) : null,
          side_b: document.getElementById('sideB').value ? Number(document.getElementById('sideB').value) : null,
          hypotenuse: document.getElementById('hypotenuse').value ? Number(document.getElementById('hypotenuse').value) : null,
        };
        break;
      }
      case 'matrix_op': {
        url = '/tools/matrix_op';
        const matrixA = JSON.parse(document.getElementById('matrixA').value || '[]');
        const matrixB = document.getElementById('matrixB').value.trim();
        payload = {
          operation: document.getElementById('operationName').value || 'multiply',
          matrix_a: matrixA,
          matrix_b: matrixB ? JSON.parse(matrixB) : null,
        };
        break;
      }
      case 'complex_op': {
        url = '/tools/complex_op';
        payload = {
          operation: document.getElementById('operationName').value || 'add',
          number_a: document.getElementById('numberA').value,
          number_b: document.getElementById('numberB').value || null,
        };
        break;
      }
      default:
        throw new Error('Ugyldig operasjon');
    }

    resultBox.textContent = 'Laster...';

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail, null, 2) : 'Noe gikk galt');
    }

    renderSolveResult(data);
  } catch (error) {
    resultBox.textContent = `Feil:\n${error.message}`;
  }
});

renderFields();
