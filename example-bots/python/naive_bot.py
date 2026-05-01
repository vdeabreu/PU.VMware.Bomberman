"""A "barely smart" Bomberman bot — a step up from random, a clear step
below the reference AI. Use it as a sanity baseline: if your bot can't
consistently beat this, you have work to do.

What it does:
- Avoids walking into walls / off the board / onto its own bomb tile
- Steps off a tile that's currently on fire, if there's a non-fire neighbour
- Occasionally drops a bomb when standing next to a destructible block
- Otherwise wanders randomly

What it does NOT do:
- Look ahead at bomb fuses (it'll happily stand next to a bomb about to blow)
- Plan an escape route before placing a bomb (it can absolutely bomb itself)
- Pathfind toward enemies, items, or the centre of the map
- Coordinate its 3 units

Stdlib only. Run with: `python3 naive_bot.py` (default port 8080).
"""
from __future__ import annotations

import json
import os
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

MOVES = {
    # Bomberland convention: up = y+1, down = y-1, right = x+1, left = x-1.
    "up":    (0,  1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1,  0),
}
BLOCKING_TYPES = {"m", "o", "w", "b"}  # walls, blocks, bombs — can't walk through
FIRE_TYPE = "x"
DESTRUCTIBLE_TYPES = {"w", "o"}
BOMB_PROBABILITY = 0.25  # when next to a destructible, 25% chance to drop a bomb


def decide_actions(game_state: dict, me: str) -> list[dict]:
    world = game_state["world"]
    w, h = world["width"], world["height"]
    entities = game_state.get("entities", [])
    unit_state = game_state.get("unit_state", {})
    my_unit_ids = game_state["agents"].get(me, {}).get("unit_ids", [])

    blocked = {(int(e["x"]), int(e["y"])) for e in entities if e.get("type") in BLOCKING_TYPES}
    fire_now = {(int(e["x"]), int(e["y"])) for e in entities if e.get("type") == FIRE_TYPE}

    actions: list[dict] = []
    for uid in my_unit_ids:
        u = unit_state.get(uid)
        if not u or u.get("hp", 0) <= 0:
            continue
        actions.append(_decide_one(uid, u, blocked, fire_now, entities, w, h))
    return actions


def _decide_one(uid, unit, blocked, fire_now, entities, w, h) -> dict:
    pos = (int(unit["coordinates"][0]), int(unit["coordinates"][1]))

    # 1. Currently on fire? Run anywhere safe-ish.
    if pos in fire_now:
        for name in random.sample(list(MOVES), len(MOVES)):
            np = _step(pos, name)
            if _in_bounds(np, w, h) and np not in blocked and np not in fire_now:
                return {"unit_id": uid, "action": name}

    # 2. Adjacent destructible + we have ammo + coin flip → drop a bomb.
    if (
        unit.get("inventory", {}).get("bombs", 0) > 0
        and _adjacent_destructible(pos, entities)
        and random.random() < BOMB_PROBABILITY
    ):
        return {"unit_id": uid, "action": "bomb"}

    # 3. Otherwise wander to any valid (non-wall, non-fire) tile.
    for name in random.sample(list(MOVES), len(MOVES)):
        np = _step(pos, name)
        if _in_bounds(np, w, h) and np not in blocked and np not in fire_now:
            return {"unit_id": uid, "action": name}

    # 4. Stuck.
    return {"unit_id": uid, "action": "stay"}


def _step(pos, action):
    dx, dy = MOVES[action]
    return (pos[0] + dx, pos[1] + dy)


def _in_bounds(p, w, h):
    return 0 <= p[0] < w and 0 <= p[1] < h


def _adjacent_destructible(pos, entities):
    for dx, dy in MOVES.values():
        np = (pos[0] + dx, pos[1] + dy)
        for e in entities:
            if (int(e["x"]), int(e["y"])) == np and e.get("type") in DESTRUCTIBLE_TYPES:
                return True
    return False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/action":
            self.send_response(404)
            self.end_headers()
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(n) or b"{}")
            actions = decide_actions(payload["game_state"], payload.get("you", "a"))
        except Exception:
            actions = []  # any failure -> all units stay this tick
        body = json.dumps({"actions": actions}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"naive_bot listening on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
