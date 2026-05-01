# Match runner

CLI that runs exactly one 1v1 match and emits a single JSON result object on stdout. **Pool generation and bracket management are out of scope** — they're yours to do in whatever tool you like.

## Minimal invocation

```bash
python3 match-runner/run_match.py \
  --team-a http://10.0.0.42:8080/action \
  --team-b http://10.0.0.55:8080/action
```

## All flags

| Flag             | Required | Default                              | Description                                                     |
|------------------|----------|--------------------------------------|-----------------------------------------------------------------|
| `--team-a URL`   | yes      | —                                    | Team A bot endpoint                                             |
| `--team-b URL`   | yes      | —                                    | Team B bot endpoint                                             |
| `--name-a NAME`  | no       | `team-a`                             | Display name for team A                                         |
| `--name-b NAME`  | no       | `team-b`                             | Display name for team B                                         |
| `--seed N`       | no       | random                               | PRNG + world seed                                               |
| `--timeout SEC`  | no       | `240`                                | Wall-clock cap for the full match                               |
| `--out-dir DIR`  | no       | `match-runner/out`                   | Where engine logs and replay artifacts are written               |
| `--keep-stack`   | no       | off                                  | Skip `docker compose down` (debugging aid)                     |

## Output

A single JSON blob, easy to append to a `.jsonl` tournament log:

```json
{
  "match_id": "a1b2c3d4",
  "status": "ok",
  "seed": 4242,
  "teams": {
    "a": { "name": "Team Red",  "endpoint": "http://10.0.0.42:8080/action" },
    "b": { "name": "Team Blue", "endpoint": "http://10.0.0.55:8080/action" }
  },
  "winner":      "a",
  "winner_name": "Team Red",
  "last_tick":   287,
  "elapsed_s":   104.3,
  "artifacts":   { "engine_logs": "...", "out_dir": "..." }
}
```

- `status`: `"ok"` | `"timeout"` | `"error"`
- `winner`: `"a"` | `"b"` | `"draw"` | `null` (null means the parser couldn't find a winner line — check `engine_logs`)

## Integrating with your pool/bracket tool

Two patterns, pick whichever fits.

### 1. Shell loop driving a `.jsonl` log

```bash
: > tournament.jsonl

for pair in $(my_pool_generator.py); do          # prints "url1,url2,name1,name2" per line
  IFS=',' read a b nameA nameB <<< "$pair"
  python3 match-runner/run_match.py \
    --team-a "$a" --team-b "$b" \
    --name-a "$nameA" --name-b "$nameB" \
    --seed $RANDOM \
    >> tournament.jsonl
done
```

Then parse `tournament.jsonl` to compute standings.

### 2. Python driver

```python
import json
import subprocess

def run(a_url, b_url, a_name, b_name, seed):
    out = subprocess.check_output([
        "python3", "match-runner/run_match.py",
        "--team-a", a_url, "--team-b", b_url,
        "--name-a", a_name, "--name-b", b_name,
        "--seed", str(seed),
    ])
    return json.loads(out)

result = run("http://10.0.0.42:8080/action", "http://10.0.0.55:8080/action",
             "Team Red", "Team Blue", 4242)
print(result["winner_name"])
```

## Concurrency

Each invocation scopes its Compose stack to a unique project name (`match-<match_id>`), so you can run multiple matches in parallel on the same host **if** you:

1. Give each adapter a unique `GAME_CONNECTION_STRING` (the Compose project name already isolates containers, but the engine's WS port 3000 is published at the host level).
2. Remove the `ports:` mapping from `docker-compose.yml` for parallel runs, and have the big-screen viewer point at each engine container's internal address instead.

For an offsite of ~8 teams, serialized matches are simpler and perfectly fine: a match takes ~100 s at 3 Hz / 300 ticks.

## Replays

The Bomberland engine writes replay files under `engine/bomberland/replays/` when `SAVE_REPLAY_ENABLED=1` (it is by default). The match runner symlinks the latest replay file into `<out-dir>/<match_id>/` — you can open it later in the Bomberland client.
