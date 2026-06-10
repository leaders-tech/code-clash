"""Compile and run untrusted bots through the configured sandbox runner.

Edit this file when Docker sandbox rules or bot process execution changes.
Copy the interface pattern here if another sandbox backend is added.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from aiohttp import ClientError, ClientSession

from backend.config import Settings


logger = logging.getLogger(__name__)


class BotRunner:
    async def compile_cpp(self, filename: str, source: str, memory_limit_mb: int) -> tuple[str, bytes | None]:
        raise NotImplementedError

    async def run_turn(self, bot: dict[str, Any], state: dict[str, Any], turn_timeout_ms: int, memory_limit_mb: int) -> dict[str, Any]:
        raise NotImplementedError


class DockerBotRunner(BotRunner):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._started = False
        self._lock = asyncio.Lock()

    async def _run(self, args: list[str], input_text: str | None = None, timeout: float = 10.0) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE if input_text is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(input_text.encode("utf-8") if input_text is not None else None), timeout=timeout)
        return process.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def ensure_started(self) -> None:
        async with self._lock:
            if self._started:
                return
            inspect_code, _, _ = await self._run(["docker", "inspect", self.settings.bot_runner_container_name], timeout=5.0)
            if inspect_code != 0:
                logger.info("Starting bot runner container %s", self.settings.bot_runner_container_name)
                await self._run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        self.settings.bot_runner_container_name,
                        "--network",
                        "none",
                        "--read-only",
                        "--tmpfs",
                        "/tmp:rw,nosuid,size=128m",
                        "--memory",
                        "512m",
                        "--cpus",
                        "1",
                        self.settings.bot_runner_image,
                    ],
                    timeout=20.0,
                )
            else:
                await self._run(["docker", "start", self.settings.bot_runner_container_name], timeout=10.0)
            self._started = True

    async def _copy_into_runner(self, local_path: Path, runner_path: str) -> None:
        await self.ensure_started()
        code, _, stderr = await self._run(["docker", "cp", str(local_path), f"{self.settings.bot_runner_container_name}:{runner_path}"], timeout=10.0)
        if code != 0:
            raise RuntimeError(f"Could not copy bot file into runner: {stderr}")

    async def _copy_from_runner(self, runner_path: str, local_path: Path) -> None:
        code, _, stderr = await self._run(["docker", "cp", f"{self.settings.bot_runner_container_name}:{runner_path}", str(local_path)], timeout=10.0)
        if code != 0:
            raise RuntimeError(f"Could not copy bot file from runner: {stderr}")

    async def compile_cpp(self, filename: str, source: str, memory_limit_mb: int) -> tuple[str, bytes | None]:
        with tempfile.TemporaryDirectory(prefix="code-clash-build-") as temp_dir:
            local_source = Path(temp_dir) / "bot.cpp"
            local_binary = Path(temp_dir) / "bot"
            local_source.write_text(source, encoding="utf-8")
            work_dir = f"/tmp/build-{os.urandom(8).hex()}"
            await self.ensure_started()
            await self._run(["docker", "exec", self.settings.bot_runner_container_name, "mkdir", "-p", work_dir], timeout=5.0)
            await self._copy_into_runner(local_source, f"{work_dir}/bot.cpp")
            code, stdout, stderr = await self._run(
                [
                    "docker",
                    "exec",
                    self.settings.bot_runner_container_name,
                    "sh",
                    "-lc",
                    f"ulimit -v {memory_limit_mb * 1024}; g++ -O2 -std=c++17 {work_dir}/bot.cpp -o {work_dir}/bot",
                ],
                timeout=30.0,
            )
            log = (stdout + stderr).strip()
            if code != 0:
                return log or "C++ build failed.", None
            await self._copy_from_runner(f"{work_dir}/bot", local_binary)
            return log or "C++ build succeeded.", local_binary.read_bytes()

    async def run_turn(self, bot: dict[str, Any], state: dict[str, Any], turn_timeout_ms: int, memory_limit_mb: int) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="code-clash-run-") as temp_dir:
            temp_path = Path(temp_dir)
            work_dir = f"/tmp/run-{os.urandom(8).hex()}"
            await self.ensure_started()
            await self._run(["docker", "exec", self.settings.bot_runner_container_name, "mkdir", "-p", work_dir], timeout=5.0)
            if bot["language"] == "python":
                local_file = temp_path / "bot.py"
                local_file.write_text(bot["source"], encoding="utf-8")
                await self._copy_into_runner(local_file, f"{work_dir}/bot.py")
                command = f"ulimit -v {memory_limit_mb * 1024}; timeout {max(turn_timeout_ms / 1000, 0.05)}s python3 {work_dir}/bot.py"
            else:
                local_file = temp_path / "bot"
                local_file.write_bytes(bot["artifact"])
                await self._copy_into_runner(local_file, f"{work_dir}/bot")
                command = f"chmod 500 {work_dir}/bot; ulimit -v {memory_limit_mb * 1024}; timeout {max(turn_timeout_ms / 1000, 0.05)}s {work_dir}/bot"
            code, stdout, stderr = await self._run(
                ["docker", "exec", "-i", self.settings.bot_runner_container_name, "sh", "-lc", command],
                input_text=json.dumps(state),
                timeout=max(turn_timeout_ms / 1000 + 2.0, 3.0),
            )
            move = stdout.strip().splitlines()[0].strip().upper() if stdout.strip() else ""
            return {"move": move, "raw": stdout[:500], "error": stderr[:500] if code != 0 else ""}


class ServiceBotRunner(BotRunner):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _post(self, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        url = f"{self.settings.bot_runner_url}{path}"
        try:
            async with ClientSession() as session:
                async with session.post(url, json=payload, timeout=timeout) as response:
                    data = await response.json()
                    if response.status >= 400:
                        raise RuntimeError(data.get("error", f"Runner service returned HTTP {response.status}."))
                    return data
        except (ClientError, TimeoutError, asyncio.TimeoutError) as exc:
            logger.exception("Bot runner service request failed")
            raise RuntimeError("Bot runner service is unavailable.") from exc

    async def compile_cpp(self, filename: str, source: str, memory_limit_mb: int) -> tuple[str, bytes | None]:
        data = await self._post(
            "/compile-cpp",
            {"filename": filename, "source": source, "memory_limit_mb": memory_limit_mb},
            timeout=35.0,
        )
        artifact_text = data.get("artifact")
        artifact = base64.b64decode(artifact_text.encode("ascii")) if isinstance(artifact_text, str) and artifact_text else None
        return str(data.get("log", "")), artifact

    async def run_turn(self, bot: dict[str, Any], state: dict[str, Any], turn_timeout_ms: int, memory_limit_mb: int) -> dict[str, Any]:
        artifact = bot.get("artifact")
        data = await self._post(
            "/run-turn",
            {
                "language": bot["language"],
                "source": bot.get("source", ""),
                "artifact": base64.b64encode(artifact).decode("ascii") if artifact else "",
                "state": state,
                "turn_timeout_ms": turn_timeout_ms,
                "memory_limit_mb": memory_limit_mb,
            },
            timeout=max(turn_timeout_ms / 1000 + 3.0, 4.0),
        )
        return {"move": str(data.get("move", "")), "raw": str(data.get("raw", ""))[:500], "error": str(data.get("error", ""))[:500]}


class ScriptedBotRunner(BotRunner):
    async def compile_cpp(self, filename: str, source: str, memory_limit_mb: int) -> tuple[str, bytes | None]:
        return "Test build succeeded.", b"test-binary"

    async def run_turn(self, bot: dict[str, Any], state: dict[str, Any], turn_timeout_ms: int, memory_limit_mb: int) -> dict[str, Any]:
        if "DOWN" in bot.get("source", ""):
            return {"move": "DOWN", "raw": "DOWN", "error": ""}
        return {"move": "RIGHT", "raw": "RIGHT", "error": ""}
