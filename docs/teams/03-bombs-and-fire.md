# Bombs and fire

The whole game is about trading blast coverage for survival. Here's the mechanics.

## Placing a bomb

Action: `{"unit_id": "c", "action": "bomb"}`

- Bomb drops on the unit's **current tile**.
- Costs 1 from `inventory.bombs` until it explodes (or until you detonate it). Default bomb count is 3 per unit.
- You cannot place a bomb on a tile that already has one.
- Once placed, the bomb is an **obstacle**: nobody (you included) can walk through it.

## Fuse / auto-detonation

A bomb carries `created` and `expires` tick numbers. It explodes automatically at `expires`. Default fuse is **30 ticks** (~10 seconds at 3 Hz).

## Remote detonation

Action: `{"unit_id": "c", "action": "detonate", "coordinates": [x, y]}`

- You can manually detonate one of **your own** bombs before its fuse runs out.
- `coordinates` = the bomb's tile.
- Bombs have a short arming delay (`BOMB_ARMED_TICKS = 5`) before they can be remotely detonated.

## Blast shape

Bombs explode in a **+ (plus) pattern**: the bomb's tile, plus tiles extending along the four cardinal directions up to the blast radius.

![Bomb blast diagram](../../assets/screenshots/bomb-blast.png)

- **Radius** = `(blast_diameter - 1) / 2`. Default `blast_diameter = 3` ⇒ radius 1 (just the bomb tile + 4 neighbours).
- Picking up a **blast powerup** increases that unit's `blast_diameter` by 2.
- A blast **stops** when it hits a solid block. The block on the boundary still takes damage (and gets destroyed if its HP reaches 0). The blast does not continue past it.

## What gets hit

Anything on a blast tile during the explosion's tick (and for `BLAST_DURATION_TICKS = 5` ticks after) takes 1 HP of damage:

- Units → `hp -= 1`. At 0 HP, the unit is removed from the board.
- Wood blocks (1 HP) → destroyed in one hit.
- Ore blocks (more HP) → need multiple hits. Each blast reduces HP by 1.
- Other bombs → **chain reaction** — they detonate immediately.
- Powerups and pickups → destroyed (lost).

Units that just took damage become `invulnerable` for `INVULNERABILITY_TICKS = 5` ticks, so you can't multi-hit the same unit with overlapping blasts.

## Chain reactions

If your blast hits an enemy's bomb, that bomb also explodes, possibly chaining further. Strategic opportunity: place one bomb where it'll detonate an enemy bomb that then hits the enemy unit.

## End-game fire

After 300 ticks, the engine starts spawning ring-of-fire tiles every `FIRE_SPAWN_INTERVAL_TICKS = 3` ticks, closing in from the outside. These fire tiles behave like any other blast: they kill units, destroy blocks, chain bombs. Don't be near the edges when this starts.

## Summary

- Bombs explode in a `+` pattern, limited by `blast_diameter` and solid blocks.
- You can remote-detonate your own bombs after the arming delay.
- Chain reactions are real; plan around them.
- The ring of fire at the end is non-negotiable. Be mid-board when it starts.

## Next

Now read [the REST API contract](04-rest-api.md) — how to actually talk to the server.
