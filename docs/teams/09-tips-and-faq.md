# Tips and FAQ

## Strategy hints

**Build a danger map first.** Before you think about offence, figure out which tiles are going to be on fire in the next ~6 ticks. A tile is dangerous if:

- There's currently a blast (`type = "x"`) on it
- A bomb is going to explode on it soon and the path between the bomb and this tile isn't blocked by a solid

Never pick an action that puts a unit onto a dangerous tile unless the unit is invulnerable this tick.

**Pathfinding is cheap.** The map is 15×15 = 225 tiles. A BFS runs in microseconds. Use it for everything: "can I escape after dropping a bomb?", "what's the shortest path to the nearest enemy / pickup?", "is this tile isolated?".

**Bombs that can't kill anything are still valuable.** Destroying wood blocks opens new paths *and* randomly drops powerups. Early-game, mining wood is usually the highest-EV play.

**Don't bomb when you can't escape.** Before dropping a bomb, simulate the blast footprint and check there's a reachable non-blast tile within the fuse duration. This is literally a BFS on `passable_tiles \ future_blast_tiles` from your current position.

**Remote detonation is underused.** A bomb with a 30-tick fuse is predictable; a bomb you can pop at tick T+7 is a trap. Place, lure, detonate.

**Unit formations.** Three units together are easy to kill with one big blast. Three units spread are harder to kill but each is weaker. Consider a "tank + flankers" split.

**Freeze powerups are brutal.** If you hit an opposing unit with a freeze, that unit is inactive for 15 ticks — that's 5 seconds, enough to corner and bomb it.

**The ring of fire is a hard deadline.** After tick 300, corners of the map become lethal fast. Start pushing toward the centre around tick 250.

**Log everything locally.** Your own debug logs are the only thing you'll have when a match goes wrong. Add a 1-line-per-tick log showing current tick, your units' positions, and chosen actions.

## FAQ

### Can I use a ML library?

Yes, any library is fine. Be mindful of cold-start time (the adapter starts hitting `/action` as soon as the match starts; if your first tick takes 2 seconds to JIT, you'll miss several ticks).

### Can I cache across ticks?

Yes. The adapter sends you a full `game_state` every tick, but there's nothing stopping you from keeping your own history in memory.

### Can I call external services?

Technically yes, but the 300 ms budget is per **your `/action` response**, not per call. Any external hop eats into that. We recommend keeping everything in-process.

### What if my bot is slow for one tick?

Your units "stay" for that tick. The match continues. Don't panic.

### What if my process crashes?

If nothing's listening on port 8080, every tick the adapter gets a connection error; your units effectively idle. Restart your process; as soon as you're back, the adapter will start getting responses again.

### Can I place two bombs on the same tick with the same unit?

No — one action per unit per tick. You can place one bomb on tick T and another on tick T+1.

### Can I move and bomb in the same tick with the same unit?

No. One action per unit per tick. Place first, move next tick.

### What's the tie-breaker?

If the game ends with both agents having surviving units, the engine picks a winner based on internal tiebreakers (total HP, last damage tick). Plan your end-game to not be in a tie.

### Can I see enemy intentions?

No. You only see current state. Read the tea leaves: a freshly placed bomb is a threat; a unit adjacent to wood is about to mine; a unit at low HP is running.

### Can I lose for misbehaving?

- Returning invalid JSON, 500s, or timing out → units "stay" that tick. No match penalty.
- Returning an action referencing a unit that isn't yours → that action is dropped; rest of your response is applied.
- Moving into a wall → unit stays. No penalty.
- Repeatedly crashing → you lose on the board (idle units die to the ring of fire).

### Can I target enemy units directly?

No direct targeting — everything happens via blasts. You can get arbitrarily close, though: step next to an enemy and drop a bomb.

### Is the map always the same?

Same map layout (symmetric 15×15 with predictable walls/blocks ratios), but **seeds vary match-to-match**, so exact block placements and spawned powerups differ. Don't hardcode tile coordinates; read them from `game_state`.

### Can I spy on the enemy's IP / code?

The adapter runs on the organizer's machine, not yours. You only see what the spec gives you. No code sharing, no side-channels.

## Contact during the event

If something is really off, flag the organizer. They can:

- Bump your bot's timeout (for everyone)
- Share your scrimmage replay
- Restart the engine if something's stuck

Good luck.
