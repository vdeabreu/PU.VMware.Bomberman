"""Reference AI HTTP server. Stdlib only."""
from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from strategy import decide_actions

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [reference-ai] %(message)s",
)
log = logging.getLogger("bot")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/action":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            me = payload.get("you", "a")
            game_state = payload["game_state"]
            actions = decide_actions(game_state, me)
        except Exception:  # noqa: BLE001
            log.exception("strategy failed; returning no-op")
            actions = []

        body = json.dumps({"actions": actions}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        # Cheap health check endpoint.
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):  # silence default access log
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    log.info("reference-ai listening on 0.0.0.0:%d", port)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
