"""Run a single Bomberland match between two team HTTP bot endpoints.

Pool / bracket logic is expected to be done by the caller. This CLI owns one
match end-to-end: it brings up an isolated engine + two adapters, waits for
the game to end (the engine self-terminates thanks to SHUTDOWN_ON_GAME_END_ENABLED),
parses the adapter / engine logs, and emits a single JSON object on stdout
describing the outcome.

Stdlib-only. Needs docker compose available on PATH.

Winner detection:
- Primary: the adapters log `endgame_state received: {'winning_agent_id': 'a'|'b'}`
  when the engine sends them the final WS packet. We grep that line.
- Fallback: heuristic regex on the engine log (Bomberland 2477 logs
  `Game completed shutting down in 5000ms` but no explicit winner line, so
  this fallback is mostly historical).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser(description="Run one Bomberland match between two team bot URLs.")
    p.add_argument("--team-a", required=True, help="Team A bot endpoint, e.g. http://team-red:8080/action")
    p.add_argument("--team-b", required=True, help="Team B bot endpoint, e.g. http://team-blue:8080/action")
    p.add_argument("--name-a", default="team-a", help="Display name for team A (used in output).")
    p.add_argument("--name-b", default="team-b", help="Display name for team B (used in output).")
    p.add_argument("--seed", type=int, default=None, help="PRNG / world seed. Defaults to a fresh random seed.")
    p.add_argument("--timeout", type=int, default=240, help="Hard wall-clock timeout for the match in seconds.")
    p.add_argument("--out-dir", default=str(REPO_ROOT / "match-runner" / "out"), help="Directory where replays are stored.")
    p.add_argument("--keep-stack", action="store_true", help="Don't tear down the compose stack afterwards (for debugging).")
    args = p.parse_args()

    if shutil.which("docker") is None:
        _fail("docker CLI not found on PATH")

    match_id = uuid.uuid4().hex[:8]
    seed = args.seed if args.seed is not None else random.randint(1, 10_000_000)
    project_name = f"match-{match_id}"
    out_dir = Path(args.out_dir) / match_id
    out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "TEAM_A_ENDPOINT": args.team_a,
            "TEAM_B_ENDPOINT": args.team_b,
            "PRNG_SEED": str(seed),
            "WORLD_SEED": str(seed),
            "COMPOSE_PROJECT_NAME": project_name,
        }
    )

    start = time.time()
    status = "error"
    winner = None
    last_tick = None
    engine_logs_path = out_dir / "engine.log"
    adapter_a_logs_path = out_dir / "adapter-a.log"
    adapter_b_logs_path = out_dir / "adapter-b.log"

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build", "game-engine", "adapter-a", "adapter-b"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )

        deadline = start + args.timeout
        engine_exited_cleanly = False
        while time.time() < deadline:
            rc = subprocess.run(
                ["docker", "compose", "ps", "-q", "game-engine"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            container_id = rc.stdout.strip()
            if not container_id:
                engine_exited_cleanly = True
                break
            inspect = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
            )
            if inspect.stdout.strip() == "false":
                engine_exited_cleanly = True
                break
            time.sleep(1.0)
        else:
            status = "timeout"

        # Always capture all logs even on timeout.
        engine_logs = _compose_logs(env, "game-engine")
        adapter_a_logs = _compose_logs(env, "adapter-a")
        adapter_b_logs = _compose_logs(env, "adapter-b")
        engine_logs_path.write_text(engine_logs)
        adapter_a_logs_path.write_text(adapter_a_logs)
        adapter_b_logs_path.write_text(adapter_b_logs)

        winner = _find_winner_in_adapter_logs(adapter_a_logs, adapter_b_logs)
        last_tick = _last_tick_from_engine_log(engine_logs)

        if engine_exited_cleanly:
            status = "ok"

    except subprocess.CalledProcessError as exc:
        _fail(f"docker compose failed: {exc}")
    finally:
        if not args.keep_stack:
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
            )

    elapsed = round(time.time() - start, 1)
    winner_name = None
    if winner == "a":
        winner_name = args.name_a
    elif winner == "b":
        winner_name = args.name_b
    elif winner == "draw":
        winner_name = "draw"

    result = {
        "match_id": match_id,
        "status": status,
        "seed": seed,
        "teams": {
            "a": {"name": args.name_a, "endpoint": args.team_a},
            "b": {"name": args.name_b, "endpoint": args.team_b},
        },
        "winner": winner,
        "winner_name": winner_name,
        "last_tick": last_tick,
        "elapsed_s": elapsed,
        "artifacts": {
            "engine_logs":   str(engine_logs_path),
            "adapter_a_logs": str(adapter_a_logs_path),
            "adapter_b_logs": str(adapter_b_logs_path),
            "out_dir":       str(out_dir),
        },
    }
    print(json.dumps(result, indent=2))
    return 0


def _compose_logs(env: dict, service: str) -> str:
    rc = subprocess.run(
        ["docker", "compose", "logs", "--no-color", service],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return rc.stdout


# Matches what the adapter logs on endgame:
#   INFO [adapter-a] endgame_state received: {'winning_agent_id': 'b'}
# Some Bomberland builds also send winning_agent_id == None (= draw / no-winner).
_ENDGAME_RE = re.compile(
    r"endgame_state received:.*?winning_agent_id'?\s*:\s*'?(?P<who>[abAB]|None|null)'?",
    re.IGNORECASE,
)


def _find_winner_in_adapter_logs(*logs: str) -> str | None:
    for log in logs:
        for m in _ENDGAME_RE.finditer(log):
            who = m.group("who").lower()
            if who in ("a", "b"):
                return who
            if who in ("none", "null"):
                return "draw"
    return None


_TICK_RE = re.compile(r"tick\s*#?(\d+)", re.IGNORECASE)


def _last_tick_from_engine_log(log: str) -> int | None:
    last = None
    for m in _TICK_RE.finditer(log):
        try:
            v = int(m.group(1))
            if last is None or v > last:
                last = v
        except ValueError:
            pass
    return last


def _fail(msg: str) -> None:
    print(json.dumps({"status": "error", "error": msg}), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
