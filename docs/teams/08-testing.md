# Testing your bot

Two ways to test: alone with synthetic requests, or against the reference AI via a live match.

## Alone — synthetic requests

```bash
curl -s localhost:8080/action \
  -H 'Content-Type: application/json' \
  -d '{"tick":0,"you":"a","game_state":{"agents":{"a":{"agent_id":"a","unit_ids":["c","e","g"]}}}}'
```

Verify:

- Response is `200 OK`
- Body is valid JSON
- `actions` is a list with your `unit_ids` only
- `action` values are from the allowed set

A fuller synthetic state (walls, bombs, enemy units) is in [`05-game-state-schema.md`](05-game-state-schema.md). Copy it into a file and replay it in a loop to stress-test your bot's latency:

```bash
time for i in $(seq 1 100); do
  curl -s localhost:8080/action -H 'Content-Type: application/json' -d @state.json > /dev/null
done
```

Anything under ~25 seconds for 100 calls (≈ 250 ms each) is safely under the 300 ms budget.

## Against the reference AI — scrimmage

Ask the organizer to run:

```bash
python3 match-runner/run_match.py \
  --team-a http://<your-ip>:8080/action --name-a "<your team>" \
  --team-b http://<ref-ai-url>/action   --name-b "reference-ai"
```

The organizer will share:

- The `winner` field from the runner's JSON output
- A link to the replay file (if you want to watch the match back)
- A `last_tick` value so you know whether you lost fast or slow

The reference AI is not invincible — it's deliberately mid-tier. If you beat it consistently, you're in contention for the tournament.

## What to test for before match day

- **Timeouts**: make sure every branch of your code completes in ≤ 300 ms. Log your per-tick compute time.
- **Crashes**: what happens if `game_state` is missing a field you expected? Return `{"actions": []}` and log — don't raise.
- **Reconnects**: if you restart your server mid-match, does it resume gracefully? The adapter will happily reconnect each tick.
- **Duplicate calls**: the adapter never sends two calls for the same tick, but be idempotent anyway.
- **Dead units**: a unit in `agents[you].unit_ids` may be **missing from `unit_state`** if it died. Don't crash on `unit_state[uid]` KeyError; just skip it.
- **Bound to 0.0.0.0**: `netstat -an | grep 8080` should show `0.0.0.0:8080`, not `127.0.0.1:8080`.

## A minimal debug log

Log one line per tick locally — really useful when something looks off during a match:

```python
print(f"tick={payload['tick']} alive={len([u for u in my_units if u in unit_state])} actions={actions}", flush=True)
```

## Next

[Tips and FAQ](09-tips-and-faq.md) — strategy hints + answers to the questions everybody asks.
