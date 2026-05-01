# Reference AI

The reference AI has three jobs:

1. **Sparring partner** during coding time. Teams can fire matches against it to gauge their progress without waiting for another team to be ready.
2. **Default opponent** in the dev stack (so `docker compose up` produces a self-playing match out of the box).
3. **Out-of-competition benchmark** at the end of the tournament — fun "champion vs. reference" exhibition match.

## Running it standalone

```bash
cd reference-ai
python3 bot.py        # listens on :8080
curl localhost:8080/health    # -> "ok"
```

Or use the Dockerfile:

```bash
docker build -t bomberman-offsite/reference-ai reference-ai
docker run --rm -p 8080:8080 bomberman-offsite/reference-ai
```

## Exposing it to teams

During coding time, publish the reference AI on the LAN (e.g. the organizer laptop's IP, port 8080). Communicate the URL in the team kickoff:

> "The reference AI is live at `http://10.0.0.1:8080/action`. Run a match against it with the match runner, or point two adapters at it to watch it play itself."

The spec explicitly tells teams they're not expected to beat it — it's a yardstick.

## Tuning difficulty

The strategy is intentionally modest:

- Flees from tiles that will be on fire within 6 ticks
- Bombs only when there's an adjacent destructible *and* a provable escape route
- Chases the nearest enemy via BFS through passable, non-dangerous tiles

All the parameters are at the top of [`reference-ai/strategy.py`](../../reference-ai/strategy.py) if you want to make it harder or softer before the event. Suggested tweaks:

| Goal                          | Change                                                                 |
|-------------------------------|------------------------------------------------------------------------|
| More aggressive bombing       | Weaken the `_has_escape_after_bomb` check (reduce `steps_budget`)      |
| Safer (less strategic)        | Increase `DANGER_HORIZON` from 6 to 10                                 |
| Harder opponent               | Replace `_decide_one` with a shallow 2-ply minimax or a canned opener |

Don't do this mid-event though — lock whatever behaviour you want before the kickoff, otherwise teams' scrimmage results become misleading.

## When the reference AI crashes

Like any bot, if `/action` returns non-200 or times out, its units simply no-op for that tick (see [`http-adapter/README.md`](../../http-adapter/README.md)). A crash of `bot.py` will, however, kill the whole process. Run it under a simple supervisor if you're worried:

```bash
while true; do python3 reference-ai/bot.py; echo "[ref-ai] crashed, restarting"; sleep 1; done
```

In the Docker stack, Compose will restart it automatically if you add `restart: unless-stopped`.
