# Example bots

Two dead-simple "random mover" reference implementations in different languages. They exist so teams have something to diff against when they start, not as strategic templates. **Teams are free to use any language** — these only illustrate the wire format.

## Python (stdlib only)

```bash
cd python
python3 random_bot.py
# serves POST /action on :8080
```

## Node (no dependencies)

```bash
cd node
node random_bot.mjs
# serves POST /action on :8080
```

## Testing your bot locally

Send it a fake request to make sure it responds:

```bash
curl -s localhost:8080/action \
  -H 'Content-Type: application/json' \
  -d '{
    "tick": 0,
    "you": "a",
    "game_state": {
      "agents": { "a": { "agent_id": "a", "unit_ids": ["c", "e", "g"] } }
    }
  }' | jq
```

Expected shape of the reply:

```json
{
  "actions": [
    { "unit_id": "c", "action": "up" },
    { "unit_id": "e", "action": "bomb" },
    { "unit_id": "g", "action": "stay" }
  ]
}
```
