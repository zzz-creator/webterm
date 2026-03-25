const API_BASE = window.API_BASE_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/i, "ws");

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
term.writeln("Controlled execution mode.");
term.writeln("Only the hidden admin Python script is interactive.");
term.writeln("");

let ws;
let connected = false;

function connect() {
  ws = new WebSocket(`${WS_BASE}/ws/run`);

  ws.onopen = () => {
    connected = true;
    term.writeln("[connected]");
  };

  ws.onmessage = (event) => {
    term.write(event.data);
  };

  ws.onerror = () => {
    term.writeln("\r\n[connection error]");
  };

  ws.onclose = () => {
    connected = false;
    term.writeln("\r\n[disconnected]");
    term.writeln("Reload page to start a new session.");
  };
}

term.onData((data) => {
  if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
    return;
  }
  ws.send(data);
});

connect();
