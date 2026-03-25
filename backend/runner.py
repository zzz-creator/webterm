"""Secure execution runner for the hidden admin script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent / "script.py"
DOCKER_IMAGE = os.getenv("RUNNER_DOCKER_IMAGE", "python:3.11-alpine")
USE_DOCKER = os.getenv("RUNNER_USE_DOCKER", "true").lower() == "true"
MAX_INPUT_SIZE = int(os.getenv("RUNNER_MAX_INPUT_SIZE", "1024"))
TIMEOUT_SECONDS = int(os.getenv("RUNNER_TIMEOUT_SECONDS", "5"))


class RunnerError(Exception):
    """Raised when script execution fails."""


def _validate_input(user_input: str) -> None:
    if len(user_input) > MAX_INPUT_SIZE:
        raise RunnerError(f"Input exceeds {MAX_INPUT_SIZE} characters.")
    if "\x00" in user_input:
        raise RunnerError("Input contains invalid null byte.")


def _run_in_docker(user_input: str) -> subprocess.CompletedProcess[str]:
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        "0.50",
        "--memory",
        "128m",
        "--pids-limit",
        "64",
        "--security-opt",
        "no-new-privileges:true",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=16m,noexec,nosuid",
        "-v",
        f"{SCRIPT_PATH}:/app/script.py:ro",
        "-w",
        "/app",
        DOCKER_IMAGE,
        "python",
        "script.py",
    ]
    return subprocess.run(
        command,
        input=user_input,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def _run_local(user_input: str) -> subprocess.CompletedProcess[str]:
    # Fallback for environments without Docker. Less isolated; use only for development.
    return subprocess.run(
        ["python", str(SCRIPT_PATH)],
        input=user_input,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def run_user_input(user_input: str) -> dict[str, str]:
    """Execute admin script with controlled input and return output/error."""
    _validate_input(user_input)

    try:
        process = _run_in_docker(user_input) if USE_DOCKER else _run_local(user_input)
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"Execution timed out after {TIMEOUT_SECONDS} seconds.") from exc
    except FileNotFoundError as exc:
        if USE_DOCKER:
            raise RunnerError("Docker is not available on this server.") from exc
        raise RunnerError("Python runtime is not available.") from exc

    output = process.stdout.strip()
    error = process.stderr.strip()

    if process.returncode != 0 and not error:
        error = f"Script failed with exit code {process.returncode}."

    return {"output": output, "error": error}
