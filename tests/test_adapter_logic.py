"""Unit tests for the HTTP adapter's state mirror and action translation.

No server or WebSocket required — imports the module and exercises internals
directly.

Run with:
    python3 -m unittest tests.test_adapter_logic -v
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "http-adapter"))

from adapter import Adapter, GameStateMirror  # noqa: E402


def _full_state() -> dict:
    return {
        "agents": {
            "a": {"agent_id": "a", "unit_ids": ["c"]},
            "b": {"agent_id": "b", "unit_ids": ["d"]},
        },
        "unit_state": {
            "c": {
                "coordinates": [1, 1],
                "hp": 3,
                "inventory": {"bombs": 3},
                "blast_diameter": 3,
                "unit_id": "c",
                "agent_id": "a",
                "invulnerable": 0,
                "stunned": 0,
            },
            "d": {
                "coordinates": [13, 13],
                "hp": 3,
                "inventory": {"bombs": 3},
                "blast_diameter": 3,
                "unit_id": "d",
                "agent_id": "b",
                "invulnerable": 0,
                "stunned": 0,
            },
        },
        "entities": [{"x": 5, "y": 5, "type": "m", "created": 0}],
        "world": {"width": 15, "height": 15},
        "tick": 0,
        "config": {
            "tick_rate_hz": 3,
            "game_duration_ticks": 300,
            "fire_spawn_interval_ticks": 3,
        },
    }


class GameStateMirrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mirror = GameStateMirror()
        self.mirror.apply(_full_state())

    def test_empty_mirror_returns_none(self) -> None:
        self.assertIsNone(GameStateMirror().snapshot())

    def test_applies_initial_full_state(self) -> None:
        snap = self.mirror.snapshot()
        self.assertIsNotNone(snap)
        self.assertEqual(snap["tick"], 0)

    def test_unit_state_event_updates_unit(self) -> None:
        self.mirror.apply(
            {
                "type": "unit_state",
                "data": {
                    "unit_id": "c",
                    "coordinates": [2, 1],
                    "hp": 3,
                    "inventory": {"bombs": 2},
                    "blast_diameter": 3,
                    "agent_id": "a",
                },
            }
        )
        unit = self.mirror.snapshot()["unit_state"]["c"]
        self.assertEqual(unit["coordinates"], [2, 1])
        self.assertEqual(unit["inventory"]["bombs"], 2)

    def test_entity_spawned_adds_bomb(self) -> None:
        self.mirror.apply(
            {
                "type": "entity_spawned",
                "data": {
                    "x": 3,
                    "y": 3,
                    "type": "b",
                    "expires": 40,
                    "hp": 1,
                    "blast_diameter": 3,
                    "owner_unit_id": "c",
                    "created": 10,
                },
            }
        )
        bombs = [e for e in self.mirror.snapshot()["entities"] if e.get("type") == "b"]
        self.assertEqual(len(bombs), 1)
        self.assertEqual(bombs[0]["x"], 3)

    def test_entity_expired_removes_entity(self) -> None:
        self.mirror.apply({"type": "entity_expired", "data": [5, 5]})
        entities = self.mirror.snapshot()["entities"]
        self.assertFalse(any(e["x"] == 5 and e["y"] == 5 for e in entities))

    def test_entity_state_updates_hp_in_place(self) -> None:
        self.mirror.apply(
            {
                "type": "entity_spawned",
                "data": {
                    "x": 3,
                    "y": 3,
                    "type": "b",
                    "expires": 40,
                    "hp": 1,
                    "blast_diameter": 3,
                    "owner_unit_id": "c",
                    "created": 10,
                },
            }
        )
        self.mirror.apply(
            {
                "type": "entity_state",
                "coordinates": [3, 3],
                "updated_entity": {
                    "x": 3,
                    "y": 3,
                    "type": "b",
                    "expires": 40,
                    "hp": 0,
                    "blast_diameter": 3,
                    "owner_unit_id": "c",
                    "created": 10,
                },
            }
        )
        bomb = [e for e in self.mirror.snapshot()["entities"] if e["x"] == 3 and e["y"] == 3][0]
        self.assertEqual(bomb["hp"], 0)

    def test_tick_packet_updates_tick_counter(self) -> None:
        # Bomberland wire format: tick number lives under payload, not top-level.
        self.mirror.apply({"type": "tick", "payload": {"tick": 42, "events": []}})
        self.assertEqual(self.mirror.snapshot()["tick"], 42)

    def test_tick_packet_applies_nested_events(self) -> None:
        self.mirror.apply(
            {
                "type": "tick",
                "payload": {
                    "tick": 7,
                    "events": [
                        {
                            "type": "unit",
                            "data": {"type": "move", "move": "up", "unit_id": "c"},
                        }
                    ],
                },
            }
        )
        snap = self.mirror.snapshot()
        self.assertEqual(snap["tick"], 7)
        self.assertEqual(snap["unit_state"]["c"]["coordinates"], [1, 2])


class NormalizeActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = Adapter("ws://fake/", "http://fake/", 300, "a")
        self.snap = {
            "agents": {
                "a": {"unit_ids": ["c", "e"]},
                "b": {"unit_ids": ["d", "f"]},
            },
        }

    def test_valid_actions_accepted(self) -> None:
        out = self.adapter._normalize_actions(
            {
                "actions": [
                    {"unit_id": "c", "action": "up"},
                    {"unit_id": "e", "action": "bomb"},
                    {"unit_id": "c", "action": "detonate", "coordinates": [4, 4]},
                ]
            },
            self.snap,
        )
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], {"type": "move", "move": "up", "unit_id": "c"})
        self.assertEqual(out[1], {"type": "bomb", "unit_id": "e"})
        self.assertEqual(
            out[2], {"type": "detonate", "coordinates": [4, 4], "unit_id": "c"}
        )

    def test_bare_list_accepted(self) -> None:
        out = self.adapter._normalize_actions(
            [{"unit_id": "c", "action": "down"}], self.snap
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["move"], "down")

    def test_enemy_and_unknown_unit_ids_dropped(self) -> None:
        out = self.adapter._normalize_actions(
            {
                "actions": [
                    {"unit_id": "d", "action": "up"},
                    {"unit_id": "zzz", "action": "up"},
                ]
            },
            self.snap,
        )
        self.assertEqual(out, [])

    def test_stay_produces_no_packet(self) -> None:
        out = self.adapter._normalize_actions(
            {"actions": [{"unit_id": "c", "action": "stay"}]}, self.snap
        )
        self.assertEqual(out, [])

    def test_detonate_without_coordinates_dropped(self) -> None:
        out = self.adapter._normalize_actions(
            {"actions": [{"unit_id": "c", "action": "detonate"}]}, self.snap
        )
        self.assertEqual(out, [])

    def test_unknown_action_dropped(self) -> None:
        out = self.adapter._normalize_actions(
            {"actions": [{"unit_id": "c", "action": "teleport"}]}, self.snap
        )
        self.assertEqual(out, [])

    def test_malformed_response_dropped(self) -> None:
        out = self.adapter._normalize_actions("not a dict or list", self.snap)
        self.assertEqual(out, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
