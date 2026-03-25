"""FastAPI backend for controlled Python execution."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from runner import RunnerError, run_user_input

RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

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
