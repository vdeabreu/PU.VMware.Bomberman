"""Minimal "random mover" Bomberman bot. Stdlib only, ~40 lines.

Run it with: python3 random_bot.py
Then point an adapter at: http://<this-host>:8080/action
"""
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

ACTIONS = ["up", "down", "left", "right", "bomb", "stay"]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        me = payload.get("you", "a")
        my_unit_ids = payload["game_state"]["agents"][me]["unit_ids"]

        actions = [
            {"unit_id": uid, "action": random.choice(ACTIONS)} for uid in my_unit_ids
        ]
        body = json.dumps({"actions": actions}).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # silence default access log
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
