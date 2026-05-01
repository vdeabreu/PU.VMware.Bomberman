"""Unit tests for the HTTP adapter's state mirror and action translation.

Doesn't spin up a server or a WebSocket — just imports the module and exercises
its internals directly. Run with: python3 tests/test_adapter_logic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "http-adapter"))

from adapter import Adapter, GameStateMirror  # noqa: E402


failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  ok:   {msg}")


# --- Mirror: full state -> event stream ---
print("GameStateMirror:")

mirror = GameStateMirror()
check(mirror.snapshot() is None, "empty mirror returns None")

full = {
    "agents": {"a": {"agent_id": "a", "unit_ids": ["c"]}, "b": {"agent_id": "b", "unit_ids": ["d"]}},
    "unit_state": {
        "c": {"coordinates": [1, 1], "hp": 3, "inventory": {"bombs": 3}, "blast_diameter": 3,
              "unit_id": "c", "agent_id": "a", "invulnerable": 0, "stunned": 0},
        "d": {"coordinates": [13, 13], "hp": 3, "inventory": {"bombs": 3}, "blast_diameter": 3,
              "unit_id": "d", "agent_id": "b", "invulnerable": 0, "stunned": 0},
    },
    "entities": [{"x": 5, "y": 5, "type": "m", "created": 0}],
    "world": {"width": 15, "height": 15},
    "tick": 0,
    "config": {"tick_rate_hz": 3, "game_duration_ticks": 300, "fire_spawn_interval_ticks": 3},
}
mirror.apply(full)
snap = mirror.snapshot()
check(snap is not None, "applies initial full state")
check(snap["tick"] == 0, "initial tick = 0")

mirror.apply({"type": "unit_state", "data": {"unit_id": "c", "coordinates": [2, 1], "hp": 3,
                                              "inventory": {"bombs": 2}, "blast_diameter": 3,
                                              "agent_id": "a"}})
snap = mirror.snapshot()
check(snap["unit_state"]["c"]["coordinates"] == [2, 1], "unit_state event moves unit c")
check(snap["unit_state"]["c"]["inventory"]["bombs"] == 2, "unit_state event decrements inventory")

mirror.apply({"type": "entity_spawned",
              "data": {"x": 3, "y": 3, "type": "b", "expires": 40, "hp": 1, "blast_diameter": 3,
                       "owner_unit_id": "c", "created": 10}})
snap = mirror.snapshot()
bombs = [e for e in snap["entities"] if e.get("type") == "b"]
check(len(bombs) == 1 and bombs[0]["x"] == 3, "entity_spawned adds a bomb")

mirror.apply({"type": "entity_expired", "data": [5, 5]})
snap = mirror.snapshot()
check(not any(e["x"] == 5 and e["y"] == 5 for e in snap["entities"]),
      "entity_expired removes metal wall at (5,5)")

mirror.apply({"type": "entity_state", "coordinates": [3, 3],
              "updated_entity": {"x": 3, "y": 3, "type": "b", "expires": 40, "hp": 0,
                                 "blast_diameter": 3, "owner_unit_id": "c", "created": 10}})
snap = mirror.snapshot()
bomb = [e for e in snap["entities"] if e["x"] == 3 and e["y"] == 3][0]
check(bomb["hp"] == 0, "entity_state updates hp in place")

mirror.apply({"type": "tick", "tick": 42})
check(mirror.snapshot()["tick"] == 42, "tick event updates tick counter")


# --- Action normalization ---
print("\nAdapter._normalize_actions:")

adapter = Adapter("ws://fake/", "http://fake/", 300, "a")
snap_for_norm = {
    "agents": {"a": {"unit_ids": ["c", "e"]}, "b": {"unit_ids": ["d", "f"]}},
}

# Valid shapes
out = adapter._normalize_actions({"actions": [
    {"unit_id": "c", "action": "up"},
    {"unit_id": "e", "action": "bomb"},
    {"unit_id": "c", "action": "detonate", "coordinates": [4, 4]},
]}, snap_for_norm)
check(len(out) == 3, "three valid actions accepted")
check(out[0] == {"type": "move", "move": "up", "unit_id": "c"}, "move translated correctly")
check(out[1] == {"type": "bomb", "unit_id": "e"}, "bomb translated correctly")
check(out[2] == {"type": "detonate", "coordinates": [4, 4], "unit_id": "c"}, "detonate translated correctly")

# Bare list also works
out = adapter._normalize_actions([{"unit_id": "c", "action": "down"}], snap_for_norm)
check(len(out) == 1 and out[0]["move"] == "down", "bare list accepted")

# Invalid unit_id (enemy's or unknown) -> dropped
out = adapter._normalize_actions({"actions": [
    {"unit_id": "d", "action": "up"},   # enemy unit
    {"unit_id": "zzz", "action": "up"}, # doesn't exist
]}, snap_for_norm)
check(out == [], "enemy/unknown unit_ids silently dropped")

# "stay" produces no packet
out = adapter._normalize_actions({"actions": [{"unit_id": "c", "action": "stay"}]}, snap_for_norm)
check(out == [], "stay action produces no engine packet")

# Detonate without coordinates -> dropped
out = adapter._normalize_actions({"actions": [{"unit_id": "c", "action": "detonate"}]}, snap_for_norm)
check(out == [], "detonate without coordinates dropped")

# Unknown action -> dropped
out = adapter._normalize_actions({"actions": [{"unit_id": "c", "action": "teleport"}]}, snap_for_norm)
check(out == [], "unknown action dropped")

# Malformed response -> empty
out = adapter._normalize_actions("not a dict or list", snap_for_norm)
check(out == [], "non-dict/list response dropped")

print()
if failures:
    print(f"FAILED: {len(failures)} assertion(s)")
    sys.exit(1)
print("All adapter unit tests passed.")
