# Engine integration

We use [CoderOne's published Bomberland engine image](https://hub.docker.com/r/gocoderone/bomberland-engine) directly. **No local build is required**, and you don't need to clone the engine source for the stack to run — `docker compose up` just pulls the prebuilt image.

The pinned tag is `gocoderone/bomberland-engine:2477` (in [`docker-compose.yml`](../docker-compose.yml)). Bump it if you want a newer engine version.

## When you might still want the engine source

Run `./pull-engine.sh` only if you want to:

- Inspect the engine source (e.g. to read the action validation schema)
- Tweak the engine and rebuild a custom image locally
- Pull pre-built starter kits / agent examples for reference

It will git-clone (or git-submodule-add, if your workspace is a git repo) the upstream `CoderOneHQ/bomberland` repo into `engine/bomberland/`. **Nothing in `docker-compose.yml` references that directory** — it's purely for offline reading and customization.

## Engine settings we override

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

## Upstream references

- API reference: https://www.gocoder.one/docs/api-reference
- Environment flags: same page, "Environment Flags" section
- Engine repo: https://github.com/CoderOneHQ/bomberland
- Image tags: https://hub.docker.com/r/gocoderone/bomberland-engine/tags
