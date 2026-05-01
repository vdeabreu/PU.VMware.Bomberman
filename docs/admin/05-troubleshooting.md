# Troubleshooting

## "Bot unreachable" — adapter never connects to a team's endpoint

The adapter logs something like:

```
WARNING [adapter-a] bot call failed at tick 3: Cannot connect to host 10.0.0.42:8080 [Errno 111]
```

**Diagnose:**

```bash
# From the organizer laptop:
curl -v http://10.0.0.42:8080/action -H 'Content-Type: application/json' -d '{"tick":0,"you":"a","game_state":{"agents":{"a":{"unit_ids":[]}}}}'
```

- If `curl` also fails → network / firewall issue on the team's machine. Ask them to check their bot is listening on `0.0.0.0` not `127.0.0.1`, and that their firewall allows inbound 8080.
- If `curl` works but the adapter doesn't → the adapter's Docker network can't reach the LAN. Make sure you're running the stack with `network_mode: host` or that the Compose network bridges to the LAN.

**Fallback:** the team's units simply no-op for that tick. The match continues; if the team's bot never recovers, their units stay idle and they lose eventually.

## Timeouts

```
WARNING [adapter-a] bot timed out at tick 18
```

Their `/action` took longer than `BOT_TIMEOUT_MS` (default 300 ms). Either:

- Their code is slow. At 3 Hz this is very forgiving — anything under 300 ms of per-tick compute works. Ask them to profile.
- They're on a laggy Wi-Fi. Move them to ethernet or increase `BOT_TIMEOUT_MS` temporarily (e.g. to 500 ms). Apply the same increase to every match once changed.

## Engine crashes / exits unexpectedly

`docker compose ps` shows `game-engine` as `Exited (1)` mid-match.

1. Check the engine logs: `docker compose logs game-engine`
2. Common causes:
   - Invalid action packet sent by an adapter (fix → restart the adapter)
   - Bad `WORLD_SEED` producing an invalid map (fix → pick a different seed, try `--seed 1`)
3. If it's truly a bug in Bomberland: re-pin `engine/pull-engine.sh` to an earlier known-good ref

## Port 3000 already in use

Another Bomberland run didn't tear down. Either:

```bash
docker ps -a | grep 3000
docker rm -f <stale-container>
```

or change the host port mapping in `docker-compose.yml` from `3000:3000` to `3001:3000` and update the big-screen's `?engine=` param accordingly.

## Big-screen shows "—" for team names

The dashboard is looking for `big-screen/state.json`. Either:

- You haven't written one yet → copy `state.example.json` to `state.json`
- You're serving the big-screen from a different directory than where `state.json` lives → use `?state=<url>` to point at the right location
- CORS: if you serve `state.json` from a different origin than the page, your browser will block the fetch. Serve them from the same `python3 -m http.server`.

## Match runner reports `winner: null`

The parser couldn't find a winner line in the engine logs. Usually means:

- The engine hit `--timeout` before the game ended → status will be `"timeout"`, inspect `artifacts.engine_logs`
- The engine output format changed in a newer Bomberland pin → update the regex in `match-runner/run_match.py:_parse_winner`

The match did happen; it's only the result extraction that failed. You can replay the match in the viewer using the replay file under `engine/bomberland/replays/`.

## Adapter keeps reconnecting

```
WARNING connection error (server rejected WebSocket connection: HTTP 404); retrying in 2s
```

The engine is not up yet, or the WebSocket URL is wrong. Double-check:

- `GAME_CONNECTION_STRING` includes `?role=agent&agentId=agentA&name=...`
- The engine container is reachable as `game-engine` on the Docker network (or on localhost if running adapters on the host)

## "A team claims their bot works but we're getting empty actions"

Ask them to hit their own endpoint with `curl` (same payload as the adapter sends). If the response shape isn't `{"actions": [...]}` or a bare array, or if `unit_id` values don't match what we sent them, we silently drop them.

Useful debug env on the adapter:

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

The adapter will then log every received action and every rejection reason.

## Docker disk space

Over a day of matches with `--build` and replays, disk usage creeps up. Clean periodically:

```bash
docker system prune -f
# and optionally:
rm -rf match-runner/out/*
```
