# HTTP Adapter

The adapter is the bridge between Bomberland's WebSocket engine and a team's HTTP bot. It lets participants write in **any language** without touching WebSockets or the engine's event reducer — they just expose one endpoint.

## Architecture

```
                      WS                           HTTP POST /action
  Bomberland engine  <-->  HTTP Adapter (this)  -------------------->  Team bot
                                                <--------------------
                                                  actions JSON response
```

One adapter process per agent slot (A or B). Concretely, a match is:

- 1 engine
- 1 adapter connected as agent A, forwarding to team A's endpoint
- 1 adapter connected as agent B, forwarding to team B's endpoint

## Configuration (env vars)

| Var                      | Required | Default | Description                                                             |
|--------------------------|----------|---------|-------------------------------------------------------------------------|
| `GAME_CONNECTION_STRING` | yes      | —       | WebSocket URL. Example: `ws://game-engine:3000/?role=agent&agentId=agentA&name=adapter-a` |
| `BOT_ENDPOINT`           | yes      | —       | URL to POST each tick. Example: `http://team-red:8080/action`           |
| `BOT_TIMEOUT_MS`         | no       | `300`   | Max time to wait for a bot response. On timeout, units do nothing this tick. |
| `MY_AGENT_ID`            | no       | `a`     | `a` or `b`, must match the `agentId` in the connection string.          |
| `LOG_LEVEL`              | no       | `INFO`  | Python logging level.                                                   |

## Wire protocol seen by the team bot

The adapter sends, once per tick:

```http
POST /action HTTP/1.1
Content-Type: application/json

{
  "tick": 42,
  "you": "a",
  "game_state": { ... full Bomberland game_state ... }
}
```

The bot replies with:

```json
{
  "actions": [
    { "unit_id": "c", "action": "up" },
    { "unit_id": "e", "action": "bomb" },
    { "unit_id": "g", "action": "detonate", "coordinates": [5, 7] }
  ]
}
```

A bare array (no `actions` wrapper) is also accepted for convenience.

### Valid `action` values

- `"up"`, `"down"`, `"left"`, `"right"` — move one tile
- `"bomb"` — place a bomb on the unit's current tile
- `"detonate"` — remotely detonate one of the unit's bombs (requires `coordinates`)
- `"stay"` — explicit no-op (equivalent to omitting the unit)

Units you own that aren't listed in the response are treated as `"stay"`.

## Failure modes and fallbacks

- **Timeout**: the adapter logs a warning and skips the tick (all units effectively "stay").
- **Non-200 response**: same as timeout.
- **Malformed JSON**: logged, same as timeout.
- **Unknown action** or **unit_id not owned**: skipped with a warning.
- **Engine unreachable at boot**: exponential backoff up to 30 s.

## Running standalone

```bash
pip install -r requirements.txt
GAME_CONNECTION_STRING='ws://localhost:3000/?role=agent&agentId=agentA&name=dev' \
BOT_ENDPOINT='http://localhost:8080/action' \
MY_AGENT_ID=a \
python adapter.py
```
