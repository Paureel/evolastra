from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CodexDispatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class MissionReceipt:
    thread_id: str
    turn_id: str


Message = dict[str, Any]
Completion = Callable[[MissionReceipt, str, str | None], None]
Started = Callable[[MissionReceipt], None]


def find_codex_executable() -> str | None:
    candidates = ("codex.cmd", "codex.exe", "codex") if os.name == "nt" else ("codex",)
    return next((path for name in candidates if (path := shutil.which(name))), None)


class CodexAppServerMission:
    def __init__(
        self,
        *,
        cwd: Path,
        prompt: str,
        command: list[str] | None = None,
        request_timeout: float = 20.0,
    ) -> None:
        self.cwd = cwd.resolve()
        self.prompt = prompt
        executable = find_codex_executable()
        if command is None and executable is None:
            raise CodexDispatchError("Codex CLI is not installed or is unavailable on PATH")
        self.command = command or [str(executable), "app-server", "--listen", "stdio://"]
        self.request_timeout = request_timeout
        self.process: subprocess.Popen[str] | None = None
        self.messages: queue.Queue[Message | BaseException | None] = queue.Queue()
        self.backlog: list[Message] = []
        self.request_id = 0
        self.receipt: MissionReceipt | None = None

    def _send(self, message: Message) -> None:
        if self.process is None or self.process.stdin is None or self.process.poll() is not None:
            raise CodexDispatchError("Codex app-server is not running")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(message, dict):
                    self.messages.put(message)
        except (OSError, UnicodeError) as error:
            self.messages.put(error)
        finally:
            self.messages.put(None)

    def _next_message(self, timeout: float) -> Message:
        try:
            message = self.messages.get(timeout=timeout)
        except queue.Empty as error:
            raise CodexDispatchError("Codex app-server did not respond in time") from error
        if message is None:
            code = self.process.poll() if self.process is not None else None
            raise CodexDispatchError(f"Codex app-server exited unexpectedly ({code})")
        if isinstance(message, BaseException):
            raise CodexDispatchError(str(message)) from message
        return message

    def _request(self, method: str, params: Message) -> Message:
        self.request_id += 1
        request_id = self.request_id
        self._send({"method": method, "id": request_id, "params": params})
        deadline = time.monotonic() + self.request_timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CodexDispatchError(f"Codex app-server timed out during {method}")
            message = self._next_message(remaining)
            if message.get("id") == request_id and "method" not in message:
                error = message.get("error")
                if isinstance(error, dict):
                    raise CodexDispatchError(str(error.get("message") or f"{method} failed"))
                result = message.get("result")
                if not isinstance(result, dict):
                    raise CodexDispatchError(f"Codex app-server returned an invalid {method} response")
                return result
            self.backlog.append(message)

    def start(self) -> MissionReceipt:
        if not self.cwd.is_dir():
            raise CodexDispatchError("The configured Codex workspace does not exist")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
                self.command,
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as error:
            raise CodexDispatchError(f"Could not start Codex app-server: {error}") from error
        threading.Thread(target=self._read_stdout, name="evolastra-codex-reader", daemon=True).start()
        try:
            self._request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "evolastra",
                        "title": "Evolastra Shipyard",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "optOutNotificationMethods": ["item/agentMessage/delta"]
                    },
                },
            )
            self._send({"method": "initialized", "params": {}})
            thread_result = self._request(
                "thread/start",
                {
                    "cwd": str(self.cwd),
                    "sandbox": "workspace-write",
                    "approvalPolicy": "never",
                    "threadSource": "user",
                    "serviceName": "evolastra",
                },
            )
            thread = thread_result.get("thread")
            thread_id = str(thread.get("id") if isinstance(thread, dict) else "")
            if not thread_id:
                raise CodexDispatchError("Codex did not return a thread id")
            turn_result = self._request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": self.prompt}],
                },
            )
            turn = turn_result.get("turn")
            turn_id = str(turn.get("id") if isinstance(turn, dict) else "")
            if not turn_id:
                raise CodexDispatchError("Codex did not return a turn id")
            self.receipt = MissionReceipt(thread_id=thread_id, turn_id=turn_id)
            return self.receipt
        except Exception:
            self.close()
            raise

    def _respond_to_unsupported_request(self, message: Message) -> None:
        if "id" in message and "method" in message:
            self._send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32601,
                        "message": "Interactive requests are unavailable in Evolastra missions",
                    },
                }
            )

    def monitor(self, completion: Completion) -> None:
        if self.receipt is None:
            raise CodexDispatchError("Mission has not started")
        status = "failed"
        error_message: str | None = "Codex app-server ended before the turn completed"
        try:
            pending = list(self.backlog)
            self.backlog.clear()
            while True:
                message = pending.pop(0) if pending else self._next_message(86_400.0)
                if "id" in message and "method" in message:
                    self._respond_to_unsupported_request(message)
                    continue
                if message.get("method") != "turn/completed":
                    continue
                params = message.get("params")
                turn = params.get("turn") if isinstance(params, dict) else None
                if not isinstance(turn, dict) or str(turn.get("id")) != self.receipt.turn_id:
                    continue
                status = str(turn.get("status") or "failed")
                turn_error = turn.get("error")
                error_message = (
                    str(turn_error.get("message"))[:1_000]
                    if isinstance(turn_error, dict) and turn_error.get("message")
                    else None
                )
                break
        except CodexDispatchError as error:
            error_message = str(error)[:1_000]
        finally:
            self.close()
            completion(self.receipt, status, error_message)

    def close(self) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


_active_lock = threading.Lock()
_active_missions: dict[str, CodexAppServerMission] = {}


def dispatch_codex_mission(
    *,
    ship_id: str,
    cwd: Path,
    prompt: str,
    completion: Completion,
    started: Started | None = None,
) -> MissionReceipt:
    with _active_lock:
        if ship_id in _active_missions:
            raise CodexDispatchError("This ship already has an active mission")
        mission = CodexAppServerMission(cwd=cwd, prompt=prompt)
        receipt = mission.start()
        _active_missions[ship_id] = mission

    try:
        if started is not None:
            started(receipt)
    except Exception:
        with _active_lock:
            _active_missions.pop(ship_id, None)
        mission.close()
        raise

    def monitor() -> None:
        try:
            mission.monitor(completion)
        finally:
            with _active_lock:
                _active_missions.pop(ship_id, None)

    threading.Thread(target=monitor, name=f"evolastra-mission-{ship_id[-8:]}", daemon=True).start()
    return receipt


def active_mission_count() -> int:
    with _active_lock:
        return len(_active_missions)


def shutdown_codex_missions() -> None:
    with _active_lock:
        missions = list(_active_missions.values())
        _active_missions.clear()
    for mission in missions:
        mission.close()
