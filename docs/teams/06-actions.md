# Actions

All the verbs your bot can return per unit, per tick.

## Cheatsheet

| Action      | When it does anything                                       | Extra fields             |
|-------------|-------------------------------------------------------------|--------------------------|
| `up`        | Target tile is inside the board, not blocked                | —                        |
| `down`      | Target tile is inside the board, not blocked                | —                        |
| `left`      | Target tile is inside the board, not blocked                | —                        |
| `right`     | Target tile is inside the board, not blocked                | —                        |
| `bomb`      | Unit has `inventory.bombs >= 1` and no bomb on its tile yet | —                        |
| `detonate`  | Unit has a still-alive bomb at `coordinates`, past arming   | `coordinates: [x, y]`    |
| `stay`      | Always                                                      | —                        |

## Movement

```json
{ "unit_id": "c", "action": "up" }
```

Moves the unit exactly one tile. `up` is `y - 1`, `down` is `y + 1`, `left` is `x - 1`, `right` is `x + 1`.

**Invalid moves are silently ignored**: if you try to move into a wall, off the board, into a bomb, or into an ore/wood block, the unit stays put. You lose the tick for that unit. Check before moving.

Two of your units can't swap tiles in a single tick either — one of the moves will fail. Watch out when you're ordering your 3 units.

## Placing a bomb

```json
{ "unit_id": "c", "action": "bomb" }
```

Drops a bomb on the unit's current tile. The unit stays on that tile *for this tick* (the bomb now blocks it). Next tick the unit can walk off the bomb tile onto a neighbouring passable tile.

Failures (silent, unit just stays):

- `inventory.bombs = 0` (all your bombs are on the board)
- a bomb is already on this tile
- the unit is stunned

## Detonating a bomb

```json
{ "unit_id": "c", "action": "detonate", "coordinates": [5, 7] }
```

Manually explodes one of **this unit's** bombs. The bomb must:

1. Exist at those coordinates (else silently dropped)
2. Belong to the unit (`owner_unit_id == unit_id`) (else silently dropped)
3. Have been placed more than 5 ticks ago (`BOMB_ARMED_TICKS`)

A detonate action triggers the same blast as an auto-expire would.

## Stay

```json
{ "unit_id": "c", "action": "stay" }
```

Explicit no-op. Equivalent to omitting the unit from your response. Use it for clarity in your code.

## Combining actions across your 3 units

Each unit acts independently; there's no global action. Example full tick:

```json
{
  "actions": [
    { "unit_id": "c", "action": "up" },
    { "unit_id": "e", "action": "bomb" },
    { "unit_id": "g", "action": "detonate", "coordinates": [7, 12] }
  ]
}
```

## Simultaneity

Everything submitted by both agents in the same tick is applied simultaneously:

- Two units moving onto the same tile → engine picks one deterministically (based on internal ordering); the other stays.
- A unit moving onto a tile where a bomb was just placed → move fails, bomb stands.
- Your bomb detonates on the same tick as an enemy unit walks into its blast → the unit takes damage.

## Next

[Quickstart](07-quickstart.md) — get a bot online in five minutes.
