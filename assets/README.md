# Assets

Illustrations used throughout the docs and kickoff slides.

## Layout

```
assets/
├── sprites/
│   └── sprites-legend.png      # The 10 tile/unit types, labelled
└── screenshots/
    ├── board-start.png         # Annotated initial board (15x15, coordinates, agent positions)
    ├── bomb-blast.png          # Single bomb blast radius + obstacle interaction
    └── end-of-match.png        # Ring-of-fire late game
```

## One-time install of the generated illustrations

The Cursor image generator writes to a path outside this workspace. To materialize them here, run once from the repo root:

```bash
./assets/install-generated.sh
```

If you prefer to do it manually:

```bash
GEN=~/.cursor/projects/Users-vdeabreu-wd-Bomberman/assets
cp "$GEN/sprites-legend.png" assets/sprites/
cp "$GEN/board-start.png"    assets/screenshots/
cp "$GEN/bomb-blast.png"     assets/screenshots/
cp "$GEN/end-of-match.png"   assets/screenshots/
```

## Regenerating

The illustrations were produced with the Cursor image generator, not checked-in source files. The original prompts are embedded as comments in `install-generated.sh` so you can re-run them if you want to tweak the style.
