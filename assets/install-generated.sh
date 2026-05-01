#!/usr/bin/env bash
# Copy the AI-generated illustrations from the Cursor project assets folder
# into this workspace. Safe to run multiple times.
#
# Image generation prompts (for regeneration reference):
#   sprites-legend.png : 2x5 labelled legend of all tile types (floor, metal,
#                        wood, ore, bomb, fire, ammo, blast powerup, freeze
#                        powerup, agent).
#   board-start.png    : 15x15 initial board with agents in opposite corners,
#                        coordinate labels on edges.
#   bomb-blast.png     : single-bomb blast diagram showing radius, blocking,
#                        and destruction of wood blocks.
#   end-of-match.png   : late-game "ring of fire" snapshot.
#
# macOS-friendly: no associative arrays, no bash 4 features.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GEN_DIR="${HOME}/.cursor/projects/Users-vdeabreu-wd-Bomberman/assets"

mkdir -p "${REPO_ROOT}/assets/sprites" "${REPO_ROOT}/assets/screenshots"

# Each entry is "<filename>:<dest-subdir>".
ENTRIES=(
    "sprites-legend.png:sprites"
    "board-start.png:screenshots"
    "bomb-blast.png:screenshots"
    "end-of-match.png:screenshots"
)

missing=0
for entry in "${ENTRIES[@]}"; do
    file="${entry%%:*}"
    subdir="${entry##*:}"
    src="${GEN_DIR}/${file}"
    dest_dir="${REPO_ROOT}/assets/${subdir}"
    if [ ! -f "${src}" ]; then
        echo "[assets] SKIP ${file} (not found at ${src})"
        missing=$((missing + 1))
        continue
    fi
    cp "${src}" "${dest_dir}/"
    echo "[assets] copied ${file} -> ${dest_dir}/"
done

if [ "${missing}" -gt 0 ]; then
    echo "[assets] ${missing} file(s) missing. Regenerate them with the Cursor image generator and rerun."
    exit 1
fi
echo "[assets] Done."
