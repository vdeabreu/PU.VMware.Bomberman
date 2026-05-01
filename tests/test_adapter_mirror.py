"""Unit tests for GameStateMirror — focused on the coordinate-update path.

The bug these tests pin down: the Bomberland engine does NOT emit a follow-up
`unit_state` event for plain moves (only for HP / stun / invulnerability
changes). The adapter therefore has to apply `unit/move` events itself, exactly
like the upstream python3 starter kit does, otherwise the mirrored game_state
shows units frozen at their initial coordinates and the bots issue moves
against a stale view of the world (cf. the ~92 % "cell is not vacant"
failure mode we hit during the dry run).

Run with: `python3 -m unittest tests.test_adapter_mirror`
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "http-adapter"))

import adapter  # noqa: E402


def _make_full_state(unit_coords=(5, 5)) -> dict:
    """Minimal full game_state packet, enough to satisfy `_looks_like_full_state`."""
    return {
        "agents": {
            "a": {"agent_id": "a", "unit_ids": ["c"]},
            "b": {"agent_id": "b", "unit_ids": ["d"]},
        },
        "unit_state": {
            "c": {
                "coordinates": list(unit_coords),
                "hp": 3,
                "inventory": {"bombs": 3},
                "blast_diameter": 3,
                "unit_id": "c",
                "agent_id": "a",
                "invulnerable": 0,
                "stunned": 0,
            },
            "d": {
                "coordinates": [10, 10],
                "hp": 3,
                "inventory": {"bombs": 3},
                "blast_diameter": 3,
                "unit_id": "d",
                "agent_id": "b",
                "invulnerable": 0,
                "stunned": 0,
            },
        },
        "entities": [],
        "world": {"width": 15, "height": 15},
        "tick": 0,
    }


class UnitMoveEventTests(unittest.TestCase):
    """Behaviour of `unit` events with `type == "move"` (engine action echo)."""

    def setUp(self) -> None:
        self.mirror = adapter.GameStateMirror()
        self.mirror.apply({"type": "game_state", "payload": _make_full_state((5, 5))})

    def _tick_with(self, *events, tick: int = 1) -> None:
        self.mirror.apply({"type": "tick", "payload": {"tick": tick, "events": list(events)}})

    def test_move_up_increments_y(self) -> None:
        # Bomberland convention: up = y + 1.
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "up", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 6])

    def test_move_down_decrements_y(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "down", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 4])

    def test_move_right_increments_x(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "right", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [6, 5])

    def test_move_left_decrements_x(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "left", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [4, 5])

    def test_consecutive_moves_accumulate(self) -> None:
        for tick, move in enumerate(["up", "up", "right", "down"], start=1):
            self._tick_with(
                {"type": "unit", "data": {"type": "move", "move": move, "unit_id": "c"}},
                tick=tick,
            )
        # 5,5 -> 5,6 -> 5,7 -> 6,7 -> 6,6
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [6, 6])

    def test_only_targeted_unit_moves(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "up", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 6])
        self.assertEqual(self.mirror.state["unit_state"]["d"]["coordinates"], [10, 10])

    def test_bomb_action_does_not_move(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "bomb", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 5])

    def test_detonate_action_does_not_move(self) -> None:
        self._tick_with(
            {"type": "unit", "data": {"type": "detonate", "unit_id": "c", "coordinates": [3, 4]}}
        )
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 5])

    def test_unit_state_event_overwrites_predicted_coordinates(self) -> None:
        """If the engine ever issues a corrective unit_state, it wins."""
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "up", "unit_id": "c"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 6])
        self._tick_with(
            {
                "type": "unit_state",
                "data": {
                    "coordinates": [9, 9],
                    "hp": 2,
                    "inventory": {"bombs": 3},
                    "blast_diameter": 3,
                    "unit_id": "c",
                    "agent_id": "a",
                    "invulnerable": 0,
                    "stunned": 0,
                },
            },
            tick=2,
        )
        unit = self.mirror.state["unit_state"]["c"]
        self.assertEqual(unit["coordinates"], [9, 9])
        self.assertEqual(unit["hp"], 2)


class UnitMoveEventRobustnessTests(unittest.TestCase):
    """The reducer should be tolerant of malformed / unknown packets."""

    def setUp(self) -> None:
        self.mirror = adapter.GameStateMirror()
        self.mirror.apply({"type": "game_state", "payload": _make_full_state((5, 5))})

    def _tick_with(self, *events, tick: int = 1) -> None:
        self.mirror.apply({"type": "tick", "payload": {"tick": tick, "events": list(events)}})

    def test_move_event_for_unknown_unit_is_ignored(self) -> None:
        self._tick_with({"type": "unit", "data": {"type": "move", "move": "up", "unit_id": "zzz"}})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 5])
        self.assertNotIn("zzz", self.mirror.state["unit_state"])

    def test_move_event_with_unknown_direction_is_ignored(self) -> None:
        self._tick_with(
            {"type": "unit", "data": {"type": "move", "move": "diagonal", "unit_id": "c"}}
        )
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 5])

    def test_move_event_with_missing_data_is_ignored(self) -> None:
        self._tick_with({"type": "unit"})
        self.assertEqual(self.mirror.state["unit_state"]["c"]["coordinates"], [5, 5])

    def test_move_event_before_initial_state_is_safe(self) -> None:
        fresh = adapter.GameStateMirror()
        # No game_state applied yet — reducer must not crash.
        fresh.apply(
            {
                "type": "tick",
                "payload": {
                    "tick": 1,
                    "events": [
                        {"type": "unit", "data": {"type": "move", "move": "up", "unit_id": "c"}}
                    ],
                },
            }
        )
        self.assertIsNone(fresh.state)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
