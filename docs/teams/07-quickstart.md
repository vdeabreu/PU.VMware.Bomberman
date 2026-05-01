# Quickstart

## Shape of the thing

You need a process that:

1. Listens on TCP `0.0.0.0:8080`
2. Accepts `POST /action` with JSON body
3. Returns `200 OK` with JSON body in ≤ 300 ms

Here are dead-simple stubs. Both ignore the game state and move randomly — just enough to see a match play out end-to-end.

## `curl` handshake

Sanity check **before** you plug into the adapter:

```bash
curl -s localhost:8080/action \
  -H 'Content-Type: application/json' \
  -d '{
    "tick": 0,
    "you": "a",
    "game_state": {
      "agents": { "a": { "agent_id": "a", "unit_ids": ["c", "e", "g"] } }
    }
  }'
```

Expected:

```json
{"actions":[{"unit_id":"c","action":"up"},{"unit_id":"e","action":"bomb"},{"unit_id":"g","action":"stay"}]}
```

If that works, your bot is ready to plug in.

## Python (stdlib only, ~30 lines)

```python
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

ACTIONS = ["up", "down", "left", "right", "bomb", "stay"]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        me = payload.get("you", "a")
        my_unit_ids = payload["game_state"]["agents"][me]["unit_ids"]

        actions = [
            {"unit_id": uid, "action": random.choice(ACTIONS)}
            for uid in my_unit_ids
        ]
        body = json.dumps({"actions": actions}).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_): pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

Run with `python3 random_bot.py`. The same file is in [`example-bots/python/random_bot.py`](../../example-bots/python/random_bot.py).

## Node (zero deps, ~25 lines)

```javascript
import http from "node:http";

const ACTIONS = ["up", "down", "left", "right", "bomb", "stay"];
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

http
  .createServer((req, res) => {
    if (req.method !== "POST" || req.url !== "/action") {
      res.writeHead(404).end();
      return;
    }
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      const { you = "a", game_state } = JSON.parse(raw || "{}");
      const unit_ids = game_state.agents[you].unit_ids;
      const actions = unit_ids.map((unit_id) => ({
        unit_id,
        action: pick(ACTIONS),
      }));
      res
        .writeHead(200, { "Content-Type": "application/json" })
        .end(JSON.stringify({ actions }));
    });
  })
  .listen(8080);
```

Same file lives at [`example-bots/node/random_bot.mjs`](../../example-bots/node/random_bot.mjs).

## Other languages

Port the above to your language — the whole contract is:

```
POST /action
Content-Type: application/json
body: {"tick": int, "you": "a"|"b", "game_state": {...}}

-> 200 OK
   Content-Type: application/json
   body: {"actions": [{"unit_id": "c", "action": "up"}, ...]}
```

## "My bot is up, now what?"

1. Bind to `0.0.0.0` (not `127.0.0.1`), so the organizer can reach you from the LAN.
2. Check your firewall allows inbound TCP 8080.
3. Tell the organizer your IP.
4. They'll schedule a scrimmage against the reference AI or another team.

## Next

[Testing](08-testing.md) — how to dogfood your bot against the reference AI before match time.
