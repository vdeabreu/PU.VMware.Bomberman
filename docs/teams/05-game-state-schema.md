# `game_state` schema

Field-by-field reference. Every tick you get a complete snapshot; no incremental updates.

## Full example

```json
{
  "agents": {
    "a": { "agent_id": "a", "unit_ids": ["c", "e", "g"] },
    "b": { "agent_id": "b", "unit_ids": ["d", "f", "h"] }
  },
  "unit_state": {
    "c": {
      "coordinates":    [1, 1],
      "hp":             3,
      "inventory":      { "bombs": 3 },
      "blast_diameter": 3,
      "unit_id":        "c",
      "agent_id":       "a",
      "invulnerable":   0,
      "stunned":        0
    },
    "d": { "coordinates": [13, 13], "hp": 3, ... },
    "...": "..."
  },
  "entities": [
    { "created": 0,  "x":  5, "y":  5, "type": "m" },
    { "created": 0,  "x":  2, "y":  1, "type": "w",  "hp": 1 },
    { "created": 0,  "x":  9, "y":  3, "type": "o",  "hp": 3 },
    { "created": 40, "x":  4, "y":  4, "type": "b",
      "owner_unit_id": "c", "expires": 70, "hp": 1, "blast_diameter": 3 },
    { "created": 60, "x":  4, "y":  3, "type": "x",
      "owner_unit_id": "c", "expires": 65 },
    { "created": 75, "x":  7, "y":  7, "type": "a",
      "expires": 115, "hp": 0 },
    { "created": 80, "x":  8, "y":  8, "type": "bp",
      "expires": 120, "hp": 0 },
    { "created": 90, "x":  9, "y":  9, "type": "fp",
      "expires": 130, "hp": 0 }
  ],
  "world":      { "width": 15, "height": 15 },
  "tick":       42,
  "config": {
    "tick_rate_hz":              3,
    "game_duration_ticks":       300,
    "fire_spawn_interval_ticks": 3
  },
  "connection": { "id": 1, "role": "agent", "agent_id": "a" }
}
```

## `agents`

```typescript
{ a: { agent_id: "a", unit_ids: string[] }, b: { agent_id: "b", unit_ids: string[] } }
```

Who plays whom. Your unit IDs are under `agents[you].unit_ids` where `you` is the top-level `you` field. They are stable across ticks — units are never renumbered.

## `unit_state[unit_id]`

| Field            | Type       | Meaning                                                                                          |
|------------------|------------|--------------------------------------------------------------------------------------------------|
| `coordinates`    | `[x, y]`   | Current tile.                                                                                    |
| `hp`             | number     | Health points. A unit at `hp = 0` is already dead and removed from the board.                    |
| `inventory.bombs`| number     | Remaining simultaneous bombs for this unit (placed bombs come back when they explode).           |
| `blast_diameter` | number     | Effective blast diameter for this unit's new bombs. Default 3. Grows with blast powerups.        |
| `unit_id`        | string     | This unit's own ID (redundant with the key, but convenient).                                      |
| `agent_id`       | `"a"`\|`"b"`| Who owns this unit.                                                                              |
| `invulnerable`   | number     | **Tick at which invulnerability ends** (inclusive). `invulnerable=0` means "never been hit".    |
| `stunned`        | number     | Tick at which stun ends (inclusive). Stunned units can't act.                                     |

Dead units are removed entirely from `unit_state`. Never assume a unit is there; check first.

## `entities`

An array of everything that isn't a unit or empty floor. Each entity has at least `created`, `x`, `y`, `type`. Additional fields depend on the type:

| `type` | Entity              | Extra fields                                                               |
|--------|---------------------|----------------------------------------------------------------------------|
| `m`    | Metal wall          | —                                                                          |
| `w`    | Wood block          | `hp` (1)                                                                   |
| `o`    | Ore block           | `hp` (several)                                                             |
| `b`    | Bomb                | `owner_unit_id`, `expires`, `hp` (always 1), `blast_diameter`              |
| `x`    | Blast / fire        | `owner_unit_id` (if from a bomb), `expires`                                |
| `a`    | Ammo pickup         | `expires`, `hp` (0 on the ground, picked up on contact)                    |
| `bp`   | Blast powerup       | `expires`, `hp`                                                            |
| `fp`   | Freeze powerup      | `expires`, `hp`                                                            |

There can be **several entities on the same tile** — e.g. a bomb dropped on a tile that also has a pickup. Don't key your internal state by `(x, y)` alone; filter by `type` too.

### `created` and `expires`

Both are **tick numbers**, not durations.

- `created = 0` means "was there at match start" (walls, initial blocks).
- `expires = 70` means "this entity disappears on tick 70".

Useful formulas:

```python
ticks_until_boom = entity["expires"] - game_state["tick"]
is_about_to_explode = ticks_until_boom <= 3
```

## `world`

```json
{ "width": 15, "height": 15 }
```

Always 15×15 in our config. Don't hardcode it anyway — read it.

## `tick`

Current tick, 0-indexed. Same value as the top-level `tick` outside `game_state`.

## `config`

Mirror of the engine settings. Useful ones for strategy:

- `tick_rate_hz` = 3
- `game_duration_ticks` = 300 → after this tick, ring of fire starts
- `fire_spawn_interval_ticks` = 3 → one fire tile spawned every 3 ticks along the shrinking ring

## `connection`

Engine bookkeeping. You can ignore everything except `agent_id`, which matches the top-level `you` field.

## Next

[Actions](06-actions.md) — the verbs your bot can return.
