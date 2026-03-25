# Controlled Python Terminal Platform

This project provides a **terminal-style web UI** backed by a **strictly controlled FastAPI execution service**.
Users can type text into the browser terminal, but they **cannot access a shell** or execute arbitrary commands.

## Security Model

- Terminal is visual-only (xterm.js UI), not a real shell.
- Backend supports both `POST /run` for one-shot execution and `GET /ws/run` for an interactive terminal stream.
- Every session executes exactly one admin-controlled file: `backend/script.py`.
- No command parsing, no file selection, no user code execution.
- Execution is sandboxed in Docker with:
  - network disabled (`--network none`)
  - read-only filesystem (`--read-only`)
  - CPU/memory/pid limits
  - timeout enforcement
- Input length validation and per-IP in-memory rate limiting are enabled.

## Project Structure

```text
frontend/
  index.html
  terminal.js
  styles.css

backend/
  main.py      # FastAPI app with /run endpoint
  runner.py    # secure execution wrapper
  script.py    # hidden/admin-controlled script executed for each request
  Dockerfile

.github/workflows/
  deploy-frontend.yml
```

## Backend API

### `POST /run` (optional one-shot mode)

Request:

```json
{
  "input": "user terminal input"
}
```

Response:

```json
{
  "output": "...",
  "error": "..."
}
```


### `GET /ws/run`

WebSocket endpoint for interactive terminal behavior.

- Browser sends keystrokes directly to the hidden Python process stdin.
- Backend streams stdout/stderr output back to the terminal.
- Users can interact with script prompts but cannot view script source from the UI.

### `GET /health`

Returns service status.

## Local Development

### 1) Run backend

```bash
cd backend
pip install fastapi "uvicorn[standard]"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Optional backend environment variables:

- `RUNNER_USE_DOCKER=true|false` (default `true`)
- `RUNNER_DOCKER_IMAGE=python:3.11-alpine`
- `RUNNER_MAX_INPUT_SIZE=1024`
- `RUNNER_TIMEOUT_SECONDS=5`
- `RATE_LIMIT_MAX_REQUESTS=30`
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `ALLOWED_ORIGINS=http://localhost:5500,https://<your-gh-pages-domain>`

### 2) Run frontend (static)

Serve `frontend/` using any static server:

```bash
python -m http.server 5500 --directory frontend
```

Open <http://localhost:5500>.

By default, frontend calls `http://localhost:8000/run`.
Set `window.API_BASE_URL` before loading `terminal.js` if needed.

## Deploy Frontend to GitHub Pages

The workflow `.github/workflows/deploy-frontend.yml` deploys `frontend/` to GitHub Pages on pushes to `main`.

Setup steps:

1. In GitHub repository settings, enable **Pages** with **GitHub Actions** as source.
2. Push to `main`.
3. Workflow publishes static frontend.

## Production Hardening Notes

- Keep backend private behind authentication and TLS.
- Restrict CORS `ALLOWED_ORIGINS` to your exact Pages URL.
- Ensure Docker is available on backend host.
- Consider stronger rate limiting (Redis-based) and request logging.
- Replace `backend/script.py` with your real business logic.
