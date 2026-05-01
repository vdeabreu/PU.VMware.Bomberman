"""Run a single Bomberland match between two team HTTP bot endpoints.

Pool / bracket logic is expected to be done by the caller. This CLI owns one
match end-to-end: it brings up an isolated engine + two adapters, waits for
the game to end (the engine self-terminates thanks to SHUTDOWN_ON_GAME_END_ENABLED),
parses the replay, and emits a single JSON object on stdout describing the outcome.

Stdlib-only. Needs docker compose available on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import random
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

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build", "game-engine", "adapter-a", "adapter-b"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )

        deadline = start + args.timeout
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
                break
            inspect = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
            )
            if inspect.stdout.strip() == "false":
                break
            time.sleep(1.0)
        else:
            status = "timeout"

        logs = subprocess.run(
            ["docker", "compose", "logs", "--no-color", "game-engine"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        engine_logs_path.write_text(logs.stdout)
        winner, last_tick = _parse_winner(logs.stdout)
        status = "ok" if winner is not None or status != "timeout" else status
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
    result = {
        "match_id": match_id,
        "status": status,
        "seed": seed,
        "teams": {"a": {"name": args.name_a, "endpoint": args.team_a},
                   "b": {"name": args.name_b, "endpoint": args.team_b}},
        "winner": winner,  # "a" | "b" | "draw" | None
        "winner_name": (args.name_a if winner == "a" else args.name_b if winner == "b" else winner),
        "last_tick": last_tick,
        "elapsed_s": elapsed,
        "artifacts": {
            "engine_logs": str(engine_logs_path),
            "out_dir": str(out_dir),
        },
    }
    print(json.dumps(result, indent=2))
    return 0


def _parse_winner(logs: str) -> tuple[str | None, int | None]:
    """Heuristic: scan the engine log output for a game-end signal and tick.

    Bomberland logs 'Winner: a' / 'Winner: b' / 'Draw' on game end. We stay
    permissive so slight format changes don't break us."""
    winner = None
    last_tick = None
    for line in logs.splitlines():
        lower = line.lower()
        if "winner" in lower:
            if "agentA" in line or "winner: a" in lower:
                winner = "a"
            elif "agentB" in line or "winner: b" in lower:
                winner = "b"
            elif "draw" in lower:
                winner = "draw"
        if "tick" in lower:
            import re
            m = re.search(r"tick[^0-9]*(\d+)", lower)
            if m:
                try:
                    last_tick = max(last_tick or 0, int(m.group(1)))
                except ValueError:
                    pass
    return winner, last_tick


def _fail(msg: str) -> None:
    print(json.dumps({"status": "error", "error": msg}), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
