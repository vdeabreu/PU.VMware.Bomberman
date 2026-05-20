#!/usr/bin/env bash
# Fetch the Bomberland engine into engine/bomberland/.
# - If this workspace is a git repo, track Bomberland as a submodule.
# - Otherwise, plain `git clone`.
# Idempotent: safe to run multiple times.
#
# Note: the offsite stack uses the prebuilt Docker image
# (gocoderone/bomberland-engine:2477). This script is only needed if you want
# the engine source locally (schema, examples, custom builds).

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

engine_present_on_disk() {
    [ -d "${SUBMODULE_PATH}/.git" ] || [ -f "${SUBMODULE_PATH}/.git" ]
}

submodule_registered() {
    if [ -f .gitmodules ] && grep -q "path = ${SUBMODULE_PATH}" .gitmodules 2>/dev/null; then
        return 0
    fi
    # Gitlink in the index (mode 160000) — submodule staged even if .gitmodules is missing.
    if [ "${is_git_repo}" = "1" ] && git ls-files --stage "${SUBMODULE_PATH}" 2>/dev/null | grep -q '^160000'; then
        return 0
    fi
    return 1
}

remove_stale_empty_dir() {
    if [ -d "${SUBMODULE_PATH}" ] && [ -z "$(ls -A "${SUBMODULE_PATH}" 2>/dev/null || true)" ]; then
        echo "[engine] Removing stale empty directory ${SUBMODULE_PATH}"
        rmdir "${SUBMODULE_PATH}"
    fi
}

init_submodule() {
    echo "[engine] Initializing submodule at ${SUBMODULE_PATH}"
    remove_stale_empty_dir
    git submodule update --init --recursive "${SUBMODULE_PATH}"
}

if engine_present_on_disk; then
    echo "[engine] Engine already present at ${SUBMODULE_PATH}, updating"
    if [ "${is_git_repo}" = "1" ] && submodule_registered; then
        git submodule update --init --recursive "${SUBMODULE_PATH}"
    fi
elif [ "${is_git_repo}" = "1" ] && submodule_registered; then
    # Common after a partial checkout or manual rmdir: registered in git, missing on disk.
    init_submodule
else
    remove_stale_empty_dir

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
echo "[engine] The running stack uses the prebuilt image from docker-compose.yml;"
echo "[engine] you do not need to build the engine unless you changed the source."
if [ "${is_git_repo}" = "0" ]; then
    echo ""
    echo "[engine] Tip: run 'git init' in ${REPO_ROOT} if you want Bomberland"
    echo "[engine]      tracked as a proper submodule rather than a nested clone."
fi
