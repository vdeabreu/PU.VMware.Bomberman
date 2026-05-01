# Bomberman Offsite

A 1v1 AI programming challenge based on [Bomberland](https://github.com/CoderOneHQ/bomberland) by CoderOne.

Teams write a tiny HTTP service that, given the game state, returns actions for each of their 3 units. Matches are streamed live on a big screen.

## Repository layout

```
.
├── engine/            # Bomberland engine fetch + offsite-tuned config
├── http-adapter/      # WebSocket<->HTTP bridge. Speaks WS to the engine, HTTP to team bots.
├── reference-ai/      # Our reference bot (sparring partner + benchmark)
├── match-runner/      # CLI to run a match between two team URLs and output JSON
├── big-screen/        # Viewer dashboard for the tournament screen
├── example-bots/      # Language-agnostic "random mover" stubs (Python, Node)
├── assets/            # Sprites, screenshots, diagrams
├── docs/
│   ├── admin/         # For the organizer (you)
│   └── teams/         # For participants
├── slides/            # Kickoff deck (markdown, Marp-compatible)
├── tests/             # Offline smoke + unit tests (no Docker needed)
└── docker-compose.yml # Dev stack: engine + 2 adapters + reference AI
```

## Offline test suite

Runs in ~3 s, no Docker, no engine, no network:

```bash
python3 tests/test_adapter_logic.py
python3 tests/smoke_test.py
```

See [`tests/README.md`](tests/README.md).

## Quick start (organizer)

```bash
# 1. Fetch the Bomberland engine as a git submodule (one-time)
./engine/pull-engine.sh

# 2. Bring up the dev stack (engine + viewer + 2 adapters + reference AI)
docker compose up --build

# 3. Open the viewer
open http://localhost:3000/

# 4. Run a one-off match between two team URLs
python match-runner/run_match.py \
  --team-a http://team-red:8080/action \
  --team-b http://team-blue:8080/action \
  --seed 42
```

## Quick start (team)

Read [`docs/teams/01-overview.md`](docs/teams/01-overview.md).

TL;DR: expose `POST /action`. On each tick, the adapter will send you the full `game_state`. Reply with a list of actions, one per unit. Any language, any framework.

## Documentation

- **Teams**: [`docs/teams/`](docs/teams/) — rules, REST contract, schema, examples, FAQ
- **Admin**: [`docs/admin/`](docs/admin/) — deployment, runbook, troubleshooting
- **Slides**: [`slides/kickoff.md`](slides/kickoff.md) — ready for projection at kickoff

## License

MIT. Built on top of [Bomberland](https://github.com/CoderOneHQ/bomberland) (MIT) by CoderOne.
