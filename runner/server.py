"""Serve compile and run requests inside the private bot-runner container.

Edit this file when sandbox execution behavior changes.
Copy this file only if another private runner service is needed.
"""

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


MAX_SOURCE_BYTES = 200_000


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length > 500_000:
        raise ValueError("Request body is too large.")
    raw_body = handler.rfile.read(length)
    data = json.loads(raw_body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    return data


def _limited_command(command: list[str], input_text: str | None, timeout: float, memory_limit_mb: int) -> subprocess.CompletedProcess[str]:
    shell_command = " ".join(shlex.quote(part) for part in command)
    return subprocess.run(
        ["sh", "-lc", f"ulimit -v {memory_limit_mb * 1024}; {shell_command}"],
        input=input_text,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def compile_cpp(payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source", ""))
    memory_limit_mb = int(payload.get("memory_limit_mb", 128))
    if not source.strip() or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {"log": "Source is required and must be under 200 KB.", "artifact": None}

    with tempfile.TemporaryDirectory(prefix="code-clash-build-") as temp_dir:
        source_path = Path(temp_dir) / "bot.cpp"
        binary_path = Path(temp_dir) / "bot"
        source_path.write_text(source, encoding="utf-8")
        result = _limited_command(["g++", "-O2", "-std=c++17", str(source_path), "-o", str(binary_path)], None, 30.0, memory_limit_mb)
        log = (result.stdout + result.stderr).strip()
        if result.returncode != 0 or not binary_path.exists():
            return {"log": log or "C++ build failed.", "artifact": None}
        artifact = base64.b64encode(binary_path.read_bytes()).decode("ascii")
        return {"log": log or "C++ build succeeded.", "artifact": artifact}


def run_turn(payload: dict[str, Any]) -> dict[str, Any]:
    language = str(payload.get("language", ""))
    state = payload.get("state", {})
    turn_timeout_ms = int(payload.get("turn_timeout_ms", 100))
    memory_limit_mb = int(payload.get("memory_limit_mb", 128))
    timeout_seconds = max(turn_timeout_ms / 1000, 0.05)
    input_text = json.dumps(state)

    with tempfile.TemporaryDirectory(prefix="code-clash-run-") as temp_dir:
        temp_path = Path(temp_dir)
        if language == "python":
            source = str(payload.get("source", ""))
            if not source.strip() or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
                return {"move": "", "raw": "", "error": "Python source is missing or too large."}
            bot_path = temp_path / "bot.py"
            bot_path.write_text(source, encoding="utf-8")
            command = ["timeout", f"{timeout_seconds}s", "python3", str(bot_path)]
        elif language == "cpp":
            artifact_text = str(payload.get("artifact", ""))
            if not artifact_text:
                return {"move": "", "raw": "", "error": "C++ artifact is missing."}
            bot_path = temp_path / "bot"
            bot_path.write_bytes(base64.b64decode(artifact_text.encode("ascii")))
            os.chmod(bot_path, 0o500)
            command = ["timeout", f"{timeout_seconds}s", str(bot_path)]
        else:
            return {"move": "", "raw": "", "error": "Unsupported bot language."}

        try:
            result = _limited_command(command, input_text, timeout_seconds + 1.0, memory_limit_mb)
        except subprocess.TimeoutExpired:
            return {"move": "", "raw": "", "error": "Bot timed out."}
        raw = result.stdout[:500]
        move = raw.strip().splitlines()[0].strip().upper() if raw.strip() else ""
        error = result.stderr[:500] if result.returncode != 0 else ""
        return {"move": move, "raw": raw, "error": error}


class RunnerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return
        _json_response(self, 404, {"error": "Not found."})

    def do_POST(self) -> None:
        try:
            payload = _read_json(self)
            if self.path == "/compile-cpp":
                _json_response(self, 200, compile_cpp(payload))
                return
            if self.path == "/run-turn":
                _json_response(self, 200, run_turn(payload))
                return
            _json_response(self, 404, {"error": "Not found."})
        except Exception as exc:
            _json_response(self, 400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"runner {self.address_string()} {format % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8090), RunnerHandler)
    print("Bot runner service listening on 0.0.0.0:8090", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
