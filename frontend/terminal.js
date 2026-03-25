const API_BASE = window.API_BASE_URL || "http://localhost:8000";

const term = new Terminal({
  convertEol: true,
  cursorBlink: true,
  fontFamily: '"Fira Code", monospace',
  theme: {
    background: "#0d1117",
    foreground: "#e6edf3",
  },
});

term.open(document.getElementById("terminal"));

const PROMPT = "> ";
let currentLine = "";
let busy = false;

function printPrompt() {
  term.write(`\r\n${PROMPT}`);
}

async function submitInput(input) {
  busy = true;
  term.write("\r\n[processing...]\r\n");

  try {
    const response = await fetch(`${API_BASE}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      const message = errBody.detail || `Request failed (${response.status})`;
      term.writeln(`error: ${message}`);
      return;
    }

    const data = await response.json();
    if (data.output) {
      term.writeln(data.output);
    }
    if (data.error) {
      term.writeln(`stderr: ${data.error}`);
    }
  } catch (error) {
    term.writeln(`error: ${error.message}`);
  } finally {
    busy = false;
    printPrompt();
  }
}

term.write("Controlled execution mode. Only admin script runs.");
term.write(`\r\n${PROMPT}`);

term.onData((data) => {
  if (busy) {
    return;
  }

  const code = data.charCodeAt(0);

  if (code === 13) {
    const captured = currentLine;
    currentLine = "";
    submitInput(captured);
    return;
  }

  if (code === 127) {
    if (currentLine.length > 0) {
      currentLine = currentLine.slice(0, -1);
      term.write("\b \b");
    }
    return;
  }

  if (code < 32) {
    return;
  }

  if (currentLine.length >= 1024) {
    return;
  }

  currentLine += data;
  term.write(data);
});
