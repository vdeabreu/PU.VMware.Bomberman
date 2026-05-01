# REST API contract

You expose **one endpoint**.

## Request

```http
POST /action HTTP/1.1
Content-Type: application/json

{
  "tick": 42,
  "you": "a",
  "game_state": {
    "agents": { "a": { "agent_id": "a", "unit_ids": ["c", "e", "g"] },
                 "b": { "agent_id": "b", "unit_ids": ["d", "f", "h"] } },
    "unit_state": { "c": { ... }, ... },
    "entities": [ { "x": 3, "y": 9, "type": "b", ... }, ... ],
    "world": { "width": 15, "height": 15 },
    "tick": 42,
    "config": { "tick_rate_hz": 3, "game_duration_ticks": 300, ... },
    "connection": { "id": 1, "role": "agent", "agent_id": "a" }
  }
}
```

Top-level fields:

| Field        | Type   | What                                                                           |
|--------------|--------|--------------------------------------------------------------------------------|
| `tick`       | number | Current game tick.                                                             |
| `you`        | `"a"` \| `"b"` | Which agent you are playing. Always consistent within a match.              |
| `game_state` | object | Full snapshot of the match (see [`05-game-state-schema.md`](05-game-state-schema.md)). |

## Response

Reply `200 OK` with JSON:

```json
{
  "actions": [
    { "unit_id": "c", "action": "up" },
    { "unit_id": "e", "action": "bomb" },
    { "unit_id": "g", "action": "detonate", "coordinates": [5, 7] }
  ]
}
```

A bare array is also accepted:

```json
[
  { "unit_id": "c", "action": "up" },
  { "unit_id": "e", "action": "bomb" }
]
```

Per-action fields:

| Field         | Type   | Required | Description                                                                       |
|---------------|--------|----------|-----------------------------------------------------------------------------------|
| `unit_id`     | string | yes      | One of your unit IDs (ignored silently if not yours).                              |
| `action`      | string | yes      | `"up"` \| `"down"` \| `"left"` \| `"right"` \| `"bomb"` \| `"detonate"` \| `"stay"` |
| `coordinates` | `[x,y]`| only if `action="detonate"` | Target bomb's tile.                                                               |

Units you own that aren't listed are treated as `"stay"`. Duplicate `unit_id` entries use the last one.

## Timing

- You have **300 ms** per tick to reply.
- If you exceed it or return non-200, your units "stay" for that tick. No disqualification; the match continues.
- Your bot is contacted only when it's your turn, i.e. every tick. No other call patterns (no websocket, no polling).

## HTTP specifics

- `Content-Type: application/json` on both request and response.
- UTF-8.
- No auth.
- No keep-alive tricks required; each tick opens a new request by default.
- You'll be hit from a LAN IP (the adapter on the organizer's laptop), not the public internet. Bind to `0.0.0.0`, not `127.0.0.1`.

## Minimal valid response (do-nothing bot)

```json
{"actions": []}
```

This is a perfectly legal reply; all your units will `"stay"` this tick. Useful as a smoke-test reply while you're wiring up the server.

## Next

[The `game_state` schema](05-game-state-schema.md) — what's actually inside that request body.
