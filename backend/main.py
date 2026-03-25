"""FastAPI backend for controlled Python execution."""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from runner import RunnerError, run_user_input

RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "script.py")
WS_IDLE_TIMEOUT_SECONDS = int(os.getenv("WS_IDLE_TIMEOUT_SECONDS", "300"))

_request_log: dict[str, Deque[float]] = defaultdict(deque)

app = FastAPI(title="Controlled Python Runner")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    input: str = Field(default="", max_length=1024)


class RunResponse(BaseModel):
    output: str
    error: str


def _enforce_rate_limit(client_ip: str) -> None:
    now = time.time()
    queue = _request_log[client_ip]

    while queue and now - queue[0] > RATE_LIMIT_WINDOW_SECONDS:
        queue.popleft()

    if len(queue) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    queue.append(now)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run_endpoint(payload: RunRequest, request: Request) -> RunResponse:
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)

    try:
        result = run_user_input(payload.input)
    except RunnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RunResponse(**result)


@app.websocket("/ws/run")
async def run_terminal(websocket: WebSocket) -> None:
    """Interactive terminal-like websocket for hidden script execution."""
    await websocket.accept()

    process = await asyncio.create_subprocess_exec(
        "python",
        SCRIPT_PATH,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def pump_stdout() -> None:
        assert process.stdout is not None
        while True:
            chunk = await process.stdout.read(1024)
            if not chunk:
                await websocket.send_text("\r\n[session ended]\r\n")
                break
            await websocket.send_text(chunk.decode("utf-8", errors="replace"))

    async def pump_stdin() -> None:
        assert process.stdin is not None
        while True:
            try:
                incoming = await asyncio.wait_for(websocket.receive_text(), timeout=WS_IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_text("\r\n[idle timeout]\r\n")
                process.terminate()
                break
            process.stdin.write(incoming.encode("utf-8"))
            await process.stdin.drain()

    stdout_task = asyncio.create_task(pump_stdout())
    stdin_task = asyncio.create_task(pump_stdin())

    try:
        await asyncio.wait({stdout_task, stdin_task}, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        stdin_task.cancel()
        stdout_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stdin_task
        with contextlib.suppress(asyncio.CancelledError):
            await stdout_task

        if process.returncode is None:
            process.terminate()
            with contextlib.suppress(ProcessLookupError):
                await process.wait()
        with contextlib.suppress(Exception):
            await websocket.close()
