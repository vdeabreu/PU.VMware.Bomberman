# Deployment

## Prerequisites

- Docker Engine **24+** with the Compose plugin (`docker compose version` should work)
- Git
- Python **3.9+** (only needed on the host running the match runner)
- Network: every team's bot endpoint must be reachable from the host running the adapters (usually the same LAN, port 8080 open on team machines)
- ~2 GB free RAM per concurrent match (engine + 2 adapters + 1 ref AI ≈ 1.5 GB)

## One-time setup

```bash
git clone <this-repo> bomberman
cd bomberman

# Fetch the Bomberland engine as a submodule (pinned to master by default)
./engine/pull-engine.sh

# Materialize the generated illustrations used by docs and slides
./assets/install-generated.sh
```

## Bring up the dev stack

```bash
docker compose up --build
```

This starts:

| Service        | Port    | What                                                              |
|----------------|---------|-------------------------------------------------------------------|
| `game-engine`  | 3000    | Bomberland engine + built-in viewer at `http://localhost:3000/`  |
| `adapter-a`    | —       | Connects as agent A, POSTs to `$TEAM_A_ENDPOINT`                  |
| `adapter-b`    | —       | Connects as agent B, POSTs to `$TEAM_B_ENDPOINT`                  |
| `reference-ai` | 8080    | Our reference bot. Default endpoint for both adapters in dev.     |

Default dev behaviour: both adapters POST to the reference AI, so the bot plays itself. Watch at `http://localhost:3000/`. The engine auto-shuts down at game end.

## Engine configuration we override

See [`engine/README.md`](../../engine/README.md) for the full table. TL;DR: we lower `TICK_RATE_HZ` from 10 to **3** so HTTP latency fits comfortably in the per-tick budget.

## LAN / tournament-day topology

On the organizer's laptop:

```
+-------------------------------+
|  Organizer laptop              |
|  * engine  (port 3000)         |
|  * adapter-a                    |
|  * adapter-b                    |
|  * match-runner (CLI)           |
|  * big-screen (port 8000)       |
+------------+------------------+
             | LAN
     +-------+-------+-------+
     |               |       |
 Team Red        Team Blue  ...
 (their bot      (their bot
  on :8080)       on :8080)
```

Each team runs their own bot on their own machine. You only need their **IP + port**. Match runner invocation uses their URLs:

```bash
python3 match-runner/run_match.py \
  --team-a http://10.0.0.42:8080/action --name-a "Team Red" \
  --team-b http://10.0.0.55:8080/action --name-b "Team Blue" \
  --seed $RANDOM
```

## Big screen

```bash
cd big-screen
python3 -m http.server 8000
# Projector browser: http://localhost:8000/?engine=http://<organizer-ip>:3000
```

See [`big-screen/README.md`](../../big-screen/README.md) for the `state.json` overlay format.

## Security note

The engine's WebSocket and the adapters' HTTP clients are intended for a trusted LAN, not the public internet. Don't expose them to WAN without a reverse proxy and auth.
