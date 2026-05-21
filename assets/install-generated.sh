#!/usr/bin/env bash
# Materialize illustration PNGs under assets/sprites/ and assets/screenshots/.
#
# Priority:
#   1. Already present in the repo  -> no-op (works on any machine, including servers)
#   2. CURSOR_ASSETS_DIR env var      -> copy from there
#   3. Known Cursor project cache dirs -> copy if found (dev laptop only)
#
# Safe to run multiple times. Exits 0 when all four files exist; exits 1 only if
# any are still missing after trying every source.
#
# Regeneration prompts (Cursor image generator):
#   sprites-legend.png : 2x5 labelled legend of all tile types
#   board-start.png    : annotated 15x15 initial board
#   bomb-blast.png     : bomb blast radius / blocking diagram
#   end-of-match.png   : late-game ring-of-fire snapshot

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

mkdir -p "${REPO_ROOT}/assets/sprites" "${REPO_ROOT}/assets/screenshots"

# "<filename>:<dest-subdir>"
ENTRIES=(
    "sprites-legend.png:sprites"
    "board-start.png:screenshots"
    "bomb-blast.png:screenshots"
    "end-of-match.png:screenshots"
)

cursor_cache_candidates() {
    # Explicit override wins.
    if [ -n "${CURSOR_ASSETS_DIR:-}" ]; then
        printf '%s\n' "${CURSOR_ASSETS_DIR}"
    fi
    # Common Cursor project-cache locations (macOS + Linux).
    local ws
    ws="$(basename "${REPO_ROOT}")"
    printf '%s\n' \
        "${HOME}/.cursor/projects/Users-vdeabreu-wd-${ws}/assets" \
        "${HOME}/.cursor/projects/Users-vdeabreu-wd-Bomberman/assets" \
        "${HOME}/.cursor/projects/Users-vdeabreu-wd-PU.VMware.Bomberman/assets" \
        "${HOME}/.cursor/projects/${ws}/assets"
}

find_source() {
    local file="$1"
    local dir candidate
    for dir in $(cursor_cache_candidates); do
        [ -n "${dir}" ] || continue
        candidate="${dir}/${file}"
        if [ -f "${candidate}" ]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done
    return 1
}

missing=0
for entry in "${ENTRIES[@]}"; do
    file="${entry%%:*}"
    subdir="${entry##*:}"
    dest="${REPO_ROOT}/assets/${subdir}/${file}"

    if [ -f "${dest}" ]; then
        echo "[assets] OK ${file} (already in assets/${subdir}/)"
        continue
    fi

    if src="$(find_source "${file}")"; then
        cp "${src}" "${dest}"
        echo "[assets] copied ${file} -> assets/${subdir}/"
        continue
    fi

    echo "[assets] MISSING ${file}"
    missing=$((missing + 1))
done

if [ "${missing}" -gt 0 ]; then
    echo ""
    echo "[assets] ${missing} file(s) still missing."
    echo "[assets] Options:"
    echo "  • git pull  (if PNGs are committed in the repo — preferred for servers)"
    echo "  • On your dev machine with Cursor, regenerate then rerun this script"
    echo "  • Or copy manually:"
    echo "      scp assets/sprites/*.png assets/screenshots/*.png user@server:~/PU.VMware.Bomberman/assets/..."
    echo "  • Or set CURSOR_ASSETS_DIR=/path/to/generated/assets ./assets/install-generated.sh"
    exit 1
fi

echo "[assets] Done — all illustrations present."
