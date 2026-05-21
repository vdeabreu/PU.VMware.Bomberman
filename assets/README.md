# Assets

Illustrations used in team docs, admin docs, and the kickoff slide deck.

## Layout

```
assets/
├── sprites/
│   └── sprites-legend.png      # The 10 tile/unit types, labelled
└── screenshots/
    ├── board-start.png         # Annotated initial board (15×15)
    ├── bomb-blast.png          # Blast radius + blocking diagram
    └── end-of-match.png        # Late-game ring-of-fire snapshot
```

These PNGs are **committed to the repo** so tournament servers do not need Cursor installed.

## Install script

```bash
./assets/install-generated.sh
```

Behavior:

- If the four PNGs already exist under `assets/sprites/` and `assets/screenshots/`, the script exits successfully immediately.
- Otherwise it tries to copy from a local Cursor project cache (dev laptop only).
- Override the cache location with `CURSOR_ASSETS_DIR=/path/to/pngs`.

On a fresh **server clone**, you usually do **not** need to run this script — `git clone` should already include the PNGs. Run it only after regenerating illustrations on a dev machine.

## Regenerating illustrations

Use the Cursor image generator (or any editor), save the four files with the names above, then either:

1. Commit them directly to `assets/sprites/` and `assets/screenshots/`, or
2. Place them in Cursor's project cache and run `./assets/install-generated.sh` on your laptop.
