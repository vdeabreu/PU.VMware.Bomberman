"""Reference AI strategy: heuristic "don't die, destroy, then bomb".

Per unit, each tick, we pick one of:

1. If standing in a tile that will be on fire soon -> flee to the nearest safe tile (BFS).
2. Else, if we can bomb a wooden/ore block adjacent to us without trapping ourselves -> bomb.
3. Else, move one step toward the nearest enemy unit (BFS) through passable tiles.
4. Else, stay put.

Coordinate system note: the Bomberland engine uses **mathematical** y axis,
i.e. "up" increases y. We honour that here.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional

Coord = tuple[int, int]

DANGER_HORIZON = 6
DEFAULT_BOMB_DURATION = 30
DEFAULT_BLAST_DIAMETER = 3

BLOCKING_ENTITY_TYPES = {"m", "o", "w"}
BOMB_TYPE = "b"
BLAST_TYPE = "x"

# Bomberland convention: up = y+1, down = y-1, right = x+1, left = x-1.
MOVES: dict[str, Coord] = {
    "up":    (0,  1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1,  0),
}


def decide_actions(game_state: dict[str, Any], me: str) -> list[dict[str, Any]]:
    # Be defensive: smoke-test payloads and edge ticks may have missing fields.
    # We bail to a no-op rather than crashing.
    if not isinstance(game_state, dict):
        return []
    world = game_state.get("world")
    if not isinstance(world, dict) or "width" not in world or "height" not in world:
        return []
    w, h = world["width"], world["height"]
    tick = game_state.get("tick", 0)

    entities = game_state.get("entities", []) or []
    unit_state = game_state.get("unit_state", {}) or {}
    agents = game_state.get("agents", {}) or {}

    my_unit_ids: list[str] = list(agents.get(me, {}).get("unit_ids", []))
    enemy_agent = "b" if me == "a" else "a"
    enemy_unit_ids: list[str] = list(agents.get(enemy_agent, {}).get("unit_ids", []))

    blocked = _static_blocked_map(entities)
    danger = _danger_map(entities, w, h, tick)

    # Live units are also obstacles. Without this, every move action that
    # targets a tile with another unit gets rejected by the engine
    # ("cell is not vacant").
    enemy_positions: list[Coord] = [
        _pos(unit_state[uid])
        for uid in enemy_unit_ids
        if uid in unit_state and unit_state[uid].get("hp", 0) > 0
    ]
    blocked |= {
        _pos(u)
        for u in unit_state.values()
        if u.get("hp", 0) > 0
    }

    actions: list[dict[str, Any]] = []
    occupied: set[Coord] = set()
    for uid in my_unit_ids:
        u = unit_state.get(uid)
        if not u or u.get("hp", 0) <= 0:
            continue
        actions.append(_decide_one(
            uid, u, blocked, danger, enemy_positions, entities, w, h, occupied, tick
        ))
    return actions


def _decide_one(uid, unit, blocked, danger, enemies, entities, w, h, occupied, tick):
    pos = _pos(unit)

    if pos in danger:
        safe = _bfs_nearest_safe(pos, blocked, danger, w, h, occupied)
        if safe is not None:
            step = _first_step(safe)
            if step is not None:
                occupied.add(_apply_step(pos, step))
                return {"unit_id": uid, "action": step}
        fallback = _any_adjacent(pos, blocked, w, h, occupied)
        if fallback is not None:
            occupied.add(_apply_step(pos, fallback))
            return {"unit_id": uid, "action": fallback}
        return {"unit_id": uid, "action": "stay"}

    if (
        unit.get("inventory", {}).get("bombs", 0) > 0
        and _adjacent_to_destructible(pos, entities)
        and _has_escape_after_bomb(pos, blocked, entities, unit, w, h)
        and not _bomb_already_at(pos, entities)
    ):
        return {"unit_id": uid, "action": "bomb"}

    if enemies:
        path = _bfs_path_to_any(pos, set(enemies), blocked, danger, w, h, occupied)
        if path:
            step = _first_step(path)
            if step is not None:
                occupied.add(_apply_step(pos, step))
                return {"unit_id": uid, "action": step}

    return {"unit_id": uid, "action": "stay"}


def _pos(unit):
    c = unit["coordinates"]
    return (int(c[0]), int(c[1]))


def _in_bounds(p, w, h):
    return 0 <= p[0] < w and 0 <= p[1] < h


def _static_blocked_map(entities):
    blocked = set()
    for e in entities:
        t = e.get("type")
        if t in BLOCKING_ENTITY_TYPES or t == BOMB_TYPE:
            blocked.add((int(e["x"]), int(e["y"])))
    return blocked


def _danger_map(entities, w, h, tick):
    """Tile -> earliest tick at which that tile will be fire."""
    danger: dict[Coord, int] = {}

    for e in entities:
        if e.get("type") == BLAST_TYPE:
            danger[(int(e["x"]), int(e["y"]))] = tick

    for e in entities:
        if e.get("type") != BOMB_TYPE:
            continue
        expires = int(e.get("expires", tick + DEFAULT_BOMB_DURATION))
        if expires - tick > DANGER_HORIZON:
            continue
        bx, by = int(e["x"]), int(e["y"])
        diameter = int(e.get("blast_diameter", DEFAULT_BLAST_DIAMETER))
        radius = max(0, (diameter - 1) // 2)
        # +/- on each axis, blocked by solid blocks.
        for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            for r in range(radius + 1):
                tile = (bx + dx * r, by + dy * r)
                if not _in_bounds(tile, w, h):
                    break
                if _tile_blocks_blast(tile, entities):
                    danger[tile] = min(danger.get(tile, expires), expires)
                    break
                danger[tile] = min(danger.get(tile, expires), expires)
                if dx == 0 and dy == 0:
                    break
    return danger


def _tile_blocks_blast(p, entities):
    for e in entities:
        if (int(e["x"]), int(e["y"])) == p and e.get("type") in BLOCKING_ENTITY_TYPES:
            return True
    return False


def _bfs_nearest_safe(start, blocked, danger, w, h, occupied):
    q: deque[tuple[Coord, list[Coord]]] = deque()
    q.append((start, [start]))
    seen = {start}
    while q:
        p, path = q.popleft()
        if p != start and p not in danger and p not in occupied:
            return path
        for (dx, dy) in MOVES.values():
            np = (p[0] + dx, p[1] + dy)
            if np in seen or not _in_bounds(np, w, h) or np in blocked:
                continue
            seen.add(np)
            q.append((np, path + [np]))
    return None


def _bfs_path_to_any(start, targets, blocked, danger, w, h, occupied):
    q: deque[tuple[Coord, list[Coord]]] = deque()
    q.append((start, [start]))
    seen = {start}
    while q:
        p, path = q.popleft()
        if p in targets:
            return path
        for (dx, dy) in MOVES.values():
            np = (p[0] + dx, p[1] + dy)
            if np in seen or not _in_bounds(np, w, h):
                continue
            if np not in targets and (np in blocked or np in danger or np in occupied):
                continue
            seen.add(np)
            q.append((np, path + [np]))
    return None


def _first_step(path):
    if len(path) < 2:
        return None
    dx = path[1][0] - path[0][0]
    dy = path[1][1] - path[0][1]
    for name, (mdx, mdy) in MOVES.items():
        if (dx, dy) == (mdx, mdy):
            return name
    return None


def _apply_step(pos, action):
    dx, dy = MOVES.get(action, (0, 0))
    return (pos[0] + dx, pos[1] + dy)


def _any_adjacent(pos, blocked, w, h, occupied):
    for name, (dx, dy) in MOVES.items():
        np = (pos[0] + dx, pos[1] + dy)
        if _in_bounds(np, w, h) and np not in blocked and np not in occupied:
            return name
    return None


def _adjacent_to_destructible(pos, entities):
    for (dx, dy) in MOVES.values():
        np = (pos[0] + dx, pos[1] + dy)
        for e in entities:
            if (int(e["x"]), int(e["y"])) == np and e.get("type") in {"w", "o"}:
                return True
    return False


def _has_escape_after_bomb(pos, blocked, entities, unit, w, h):
    diameter = int(unit.get("blast_diameter", DEFAULT_BLAST_DIAMETER))
    radius = max(0, (diameter - 1) // 2)
    fake_blast: set[Coord] = set()
    for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        for r in range(radius + 1):
            tile = (pos[0] + dx * r, pos[1] + dy * r)
            if not _in_bounds(tile, w, h):
                break
            fake_blast.add(tile)
            if _tile_blocks_blast(tile, entities) and (dx, dy) != (0, 0):
                break
            if (dx, dy) == (0, 0):
                break

    blocked_with_self_bomb = blocked | {pos}
    q: deque[tuple[Coord, int]] = deque()
    q.append((pos, 0))
    seen = {pos}
    steps_budget = DEFAULT_BOMB_DURATION - 2
    while q:
        p, d = q.popleft()
        if p != pos and p not in fake_blast:
            return True
        if d >= steps_budget:
            continue
        for (dx, dy) in MOVES.values():
            np = (p[0] + dx, p[1] + dy)
            if (
                np in seen
                or not _in_bounds(np, w, h)
                or np in blocked_with_self_bomb
            ):
                continue
            seen.add(np)
            q.append((np, d + 1))
    return False


def _bomb_already_at(pos, entities):
    for e in entities:
        if (int(e["x"]), int(e["y"])) == pos and e.get("type") == BOMB_TYPE:
            return True
    return False
