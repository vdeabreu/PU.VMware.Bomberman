# Reference AI

A straightforward bot used as a sparring partner for teams during coding time, and as an out-of-competition benchmark during the tournament.

## Strategy in one paragraph

Per unit, per tick, pick the **first** of:

1. **Flee** if standing on a tile that will be on fire within `DANGER_HORIZON=6` ticks. BFS to the nearest non-dangerous, passable tile.
2. **Bomb** if adjacent to a destructible block (wood or ore), *and* we still have an escape route within the bomb's fuse.
3. **Chase** the nearest enemy unit via BFS, stepping only through passable, non-dangerous tiles.
4. Otherwise **stay** put.

No search deeper than "one hop". This is deliberately a mid-tier bot: hard enough to beat naive random movers, easy enough for a motivated team to outplay by lunchtime.

## Run it

```bash
cd reference-ai
python3 bot.py          # listens on :8080
curl localhost:8080/health
```

Expose `POST /action` exactly like teams do — because that's what it is.

## Tune or replace

- All magic numbers live at the top of `strategy.py` (`DANGER_HORIZON`, `DEFAULT_BOMB_DURATION`, `DEFAULT_BLAST_DIAMETER`).
- Swap the entirety of `decide_actions(...)` for your own if you want a stronger benchmark.
