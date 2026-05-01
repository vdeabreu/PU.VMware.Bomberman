# Engine integration

We do **not** fork the Bomberland C++ source into this repo. Instead, we consume it via git submodule and run its pre-built images through our `docker-compose.yml`.

## Fetching the engine

```bash
./pull-engine.sh
```

This adds `CoderOneHQ/bomberland` as a submodule under `engine/bomberland/` and pins it to a known-good commit.

## What we tweak

Our `docker-compose.yml` overrides a handful of env vars vs. the upstream defaults, tuned for an HTTP-mediated offsite where per-tick latency can reach ~300 ms:

| Var                          | Upstream default | Our offsite value | Why                                                                 |
|------------------------------|------------------|-------------------|---------------------------------------------------------------------|
| `TICK_RATE_HZ`               | 10               | **3**             | Gives bots ~330 ms per tick, which comfortably absorbs HTTP latency. |
| `GAME_DURATION_TICKS`        | 200              | **300**           | ~100 s of real-time play at 3 Hz — long enough to be entertaining. |
| `FIRE_SPAWN_INTERVAL_TICKS`  | 2                | **3**             | Keeps late-game ring-of-fire pace matched to the slower tick rate. |
| `PRNG_SEED` / `WORLD_SEED`   | 1234             | **per match**     | Match runner passes a fresh seed to each match for variety.        |
| `ADMIN_ROLE_ENABLED`         | 0                | **0**             | No admin stepping in tournament.                                    |
| `SAVE_REPLAY_ENABLED`        | 1                | **1**             | Every tournament match keeps a replay file.                         |
| `SHUTDOWN_ON_GAME_END_ENABLED` | 1              | **1**             | The match-runner expects the engine to exit when the game ends.    |

All other settings keep upstream defaults (15x15 map, 3 units per agent, 3 HP, etc.).

## Upstream docs

- API reference: https://www.gocoder.one/docs/api-reference
- Environment flags: same page, "Environment Flags" section
- Engine repo: https://github.com/CoderOneHQ/bomberland
