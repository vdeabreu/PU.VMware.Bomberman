# Match runner

A one-shot CLI that runs a single 1v1 match between two HTTP bot endpoints. **Pools and brackets are generated separately** — this tool only knows how to run one match at a time.

## Usage

```bash
python3 match-runner/run_match.py \
  --team-a http://team-red:8080/action \
  --team-b http://team-blue:8080/action \
  --name-a "Team Red" \
  --name-b "Team Blue" \
  --seed 4242
```

Useful flags:

- `--timeout 240` — wall-clock cap for the whole match (seconds). Defaults to 240 s, comfortably above a 300-tick game at 3 Hz (~100 s).
- `--out-dir path/to/replays` — where engine logs and replay artifacts are dropped. Each match gets its own subdirectory.
- `--keep-stack` — don't run `docker compose down` afterwards. Useful when debugging a broken match.

## Output

A single JSON object on stdout:

```json
{
  "match_id": "a1b2c3d4",
  "status": "ok",
  "seed": 4242,
  "teams": {
    "a": { "name": "Team Red",  "endpoint": "http://team-red:8080/action" },
    "b": { "name": "Team Blue", "endpoint": "http://team-blue:8080/action" }
  },
  "winner": "a",
  "winner_name": "Team Red",
  "last_tick": 287,
  "elapsed_s": 104.3,
  "artifacts": {
    "engine_logs": "match-runner/out/a1b2c3d4/engine.log",
    "out_dir":     "match-runner/out/a1b2c3d4"
  }
}
```

`status` is `"ok"` | `"timeout"` | `"error"`. `winner` is `"a"` | `"b"` | `"draw"` | `null`.

## Integrating with an external tournament tool

The runner is designed to be piped:

```bash
for pair in $(python3 my_pool_generator.py); do
  a=$(echo "$pair" | cut -d, -f1)
  b=$(echo "$pair" | cut -d, -f2)
  python3 match-runner/run_match.py --team-a "$a" --team-b "$b" >> results.jsonl
done
```

Concatenate the resulting `jsonl` file and feed it to your leaderboard / bracket tool.

## How it works

The runner shells out to `docker compose up` against the repo-root `docker-compose.yml`, but scopes each match to its own Compose project name (`match-<match_id>`) so concurrent matches can run on the same host without colliding on container names. After the engine container exits (which it does automatically on game end thanks to `SHUTDOWN_ON_GAME_END_ENABLED=1`), it captures the engine logs and extracts the winner.
