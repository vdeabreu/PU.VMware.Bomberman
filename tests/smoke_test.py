"""End-to-end smoke test without Docker / engine.

Boots the reference AI and the random-mover stub as subprocesses, fabricates a
handful of realistic game_state packets, POSTs them exactly like the HTTP
adapter would, and verifies the contract on each response.

Run with: python3 tests/smoke_test.py
Exits 0 on success, non-zero and prints a diff on failure.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID_ACTIONS = {"up", "down", "left", "right", "bomb", "detonate", "stay"}


def make_state(tick: int, agent_a_in_corner: bool = True) -> dict:
    return {
        "agents": {
            "a": {"agent_id": "a", "unit_ids": ["c", "e", "g"]},
            "b": {"agent_id": "b", "unit_ids": ["d", "f", "h"]},
        },
        "unit_state": {
            "c": _unit("c", "a", (1, 1) if agent_a_in_corner else (7, 7)),
            "e": _unit("e", "a", (1, 2) if agent_a_in_corner else (7, 8)),
            "g": _unit("g", "a", (2, 1) if agent_a_in_corner else (8, 7)),
            "d": _unit("d", "b", (13, 13)),
            "f": _unit("f", "b", (13, 12)),
            "h": _unit("h", "b", (12, 13)),
        },
        "entities": [
            {"x": 5, "y": 5, "type": "m", "created": 0},
            {"x": 2, "y": 1, "type": "w", "hp": 1, "created": 0},
            {"x": 9, "y": 3, "type": "o", "hp": 3, "created": 0},
            {"x": 4, "y": 4, "type": "b", "hp": 1, "created": max(0, tick - 5),
             "expires": tick + 10, "blast_diameter": 3, "owner_unit_id": "c"},
        ],
        "world": {"width": 15, "height": 15},
        "tick": tick,
        "config": {
            "tick_rate_hz": 3,
            "game_duration_ticks": 300,
            "fire_spawn_interval_ticks": 3,
        },
        "connection": {"id": 1, "role": "agent", "agent_id": "a"},
    }


def _unit(uid: str, agent: str, pos: tuple[int, int]) -> dict:
    return {
        "coordinates": list(pos),
        "hp": 3,
        "inventory": {"bombs": 3},
        "blast_diameter": 3,
        "unit_id": uid,
        "agent_id": agent,
        "invulnerable": 0,
        "stunned": 0,
    }


def wait_for_port(port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=0.3) as r:
                if r.status == 200:
                    return True
        except urllib.error.URLError:
            pass
        except Exception:
            pass
        # Also try POST because the random bot doesn't have /health.
        try:
            req = urllib.request.Request(
                f"http://localhost:{port}/action",
                data=json.dumps({"tick": 0, "you": "a", "game_state": make_state(0)}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=0.3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def call_bot(port: int, state: dict, me: str) -> tuple[int, dict]:
    payload = {"tick": state["tick"], "you": me, "game_state": state}
    req = urllib.request.Request(
        f"http://localhost:{port}/action",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1.0) as r:
        body = json.loads(r.read().decode())
        return r.status, body


def validate_response(body, my_unit_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if isinstance(body, dict) and "actions" in body:
        actions = body["actions"]
    elif isinstance(body, list):
        actions = body
    else:
        return [f"response must be object with 'actions' or a bare list; got {type(body).__name__}"]
    if not isinstance(actions, list):
        return [f"'actions' must be a list; got {type(actions).__name__}"]
    seen: set[str] = set()
    for i, a in enumerate(actions):
        if not isinstance(a, dict):
            errors.append(f"actions[{i}] is not an object")
            continue
        uid = a.get("unit_id")
        if uid not in my_unit_ids:
            errors.append(f"actions[{i}].unit_id={uid!r} is not one of {sorted(my_unit_ids)}")
        if uid in seen:
            errors.append(f"actions[{i}].unit_id={uid!r} is duplicated")
        seen.add(uid)
        action = a.get("action")
        if action not in VALID_ACTIONS:
            errors.append(f"actions[{i}].action={action!r} not in {sorted(VALID_ACTIONS)}")
        if action == "detonate":
            coords = a.get("coordinates")
            if not (isinstance(coords, list) and len(coords) == 2 and all(isinstance(c, int) for c in coords)):
                errors.append(f"actions[{i}].coordinates missing/malformed for detonate")
    return errors


def start_bot(cmd: list[str], cwd: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(port)
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    if not wait_for_port(port, timeout=5.0):
        proc.send_signal(signal.SIGTERM)
        raise RuntimeError(f"bot did not come up on port {port}")
    return proc


def kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=3)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


class BotRunner:
    def __init__(self, name: str, cmd: list[str], cwd: Path, port: int) -> None:
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.port = port
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "BotRunner":
        self.proc = start_bot(self.cmd, self.cwd, self.port)
        return self

    def __exit__(self, *_):
        if self.proc:
            kill(self.proc)


def main() -> int:
    failures: list[str] = []

    scenarios = [
        ("reference-ai", ["python3", "bot.py"], REPO_ROOT / "reference-ai", 9100),
        ("random-bot",   ["python3", "random_bot.py"], REPO_ROOT / "example-bots" / "python", 9101),
    ]

    # Random bot doesn't read PORT; we'll hit its hardcoded 8080 via a wrapper.
    # Patch: regenerate a tweaked random bot that uses PORT env var.
    rb_patched = REPO_ROOT / "tests" / "_random_bot_patched.py"
    rb_original = (REPO_ROOT / "example-bots" / "python" / "random_bot.py").read_text()
    rb_patched.write_text(
        rb_original.replace(
            'HTTPServer(("0.0.0.0", 8080)',
            'HTTPServer(("0.0.0.0", int(__import__("os").environ.get("PORT","8080")))',
        )
    )
    scenarios[1] = ("random-bot", ["python3", str(rb_patched)], REPO_ROOT, 9101)

    try:
        for bot_name, cmd, cwd, port in scenarios:
            print(f"[{bot_name}] starting on :{port}")
            try:
                with BotRunner(bot_name, cmd, cwd, port):
                    for tick in (0, 5, 50, 150, 280):
                        state = make_state(tick, agent_a_in_corner=(tick < 100))
                        my_units = set(state["agents"]["a"]["unit_ids"])
                        t0 = time.perf_counter()
                        status, body = call_bot(port, state, "a")
                        dt_ms = (time.perf_counter() - t0) * 1000
                        if status != 200:
                            failures.append(f"[{bot_name}] tick={tick} HTTP {status}")
                            continue
                        errs = validate_response(body, my_units)
                        if errs:
                            failures.append(
                                f"[{bot_name}] tick={tick} contract violations:\n  - "
                                + "\n  - ".join(errs)
                                + f"\n  body={json.dumps(body)[:200]}"
                            )
                        else:
                            print(f"[{bot_name}] tick={tick:>3}  {dt_ms:6.2f} ms  OK  body={json.dumps(body)[:80]}")

                        # Latency budget: must be far below 300ms for a reasonable match.
                        if dt_ms > 300:
                            failures.append(f"[{bot_name}] tick={tick} took {dt_ms:.0f}ms (>300ms budget)")
            except Exception as exc:
                failures.append(f"[{bot_name}] fatal: {exc}")
    finally:
        try:
            rb_patched.unlink(missing_ok=True)
        except Exception:
            pass

    print()
    if failures:
        print("=" * 60)
        print(f"FAILED: {len(failures)} problem(s)")
        for f in failures:
            print("-", f)
        return 1

    print("=" * 60)
    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
