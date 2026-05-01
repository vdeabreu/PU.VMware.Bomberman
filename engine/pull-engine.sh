#!/usr/bin/env bash
# Fetch the Bomberland engine into engine/bomberland/.
# - If this workspace is itself a git repo, add Bomberland as a submodule.
# - Otherwise, plain `git clone`. Either way you end up with engine/bomberland/
#   pinned to the chosen ref.
# Idempotent: running twice is a no-op.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUBMODULE_PATH="engine/bomberland"
REMOTE_URL="https://github.com/CoderOneHQ/bomberland.git"
# Pin to a known-good ref. Bump as needed.
PIN_REF="master"

cd "${REPO_ROOT}"

is_git_repo=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    is_git_repo=1
fi

# Already fetched?
if [ -d "${SUBMODULE_PATH}/.git" ] || [ -f "${SUBMODULE_PATH}/.git" ]; then
    echo "[engine] Engine already present at ${SUBMODULE_PATH}, updating"
    if [ "${is_git_repo}" = "1" ] && [ -f .gitmodules ] && grep -q "${SUBMODULE_PATH}" .gitmodules; then
        git submodule update --init --recursive "${SUBMODULE_PATH}"
    fi
else
    if [ -d "${SUBMODULE_PATH}" ] && [ -z "$(ls -A "${SUBMODULE_PATH}")" ]; then
        echo "[engine] Removing stale empty directory ${SUBMODULE_PATH}"
        rmdir "${SUBMODULE_PATH}"
    fi

    if [ "${is_git_repo}" = "1" ]; then
        echo "[engine] Adding ${REMOTE_URL} as submodule at ${SUBMODULE_PATH}"
        git submodule add "${REMOTE_URL}" "${SUBMODULE_PATH}"
    else
        echo "[engine] Workspace is not a git repo; using plain clone"
        echo "[engine] Cloning ${REMOTE_URL} into ${SUBMODULE_PATH}"
        git clone "${REMOTE_URL}" "${SUBMODULE_PATH}"
    fi
fi

cd "${SUBMODULE_PATH}"
git fetch --quiet origin "${PIN_REF}"
git checkout --quiet "${PIN_REF}"
echo "[engine] Checked out $(git rev-parse --short HEAD) on ${PIN_REF}"

echo ""
echo "[engine] Done."
echo "[engine] Next step: docker compose build game-engine"
if [ "${is_git_repo}" = "0" ]; then
    echo ""
    echo "[engine] Tip: run 'git init' in ${REPO_ROOT} if you want Bomberland"
    echo "[engine]      tracked as a proper submodule rather than a nested clone."
fi
