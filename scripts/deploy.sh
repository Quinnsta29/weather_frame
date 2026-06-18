#!/usr/bin/env bash
#
# Deploy WeatherFrame to this Raspberry Pi. Invoked by the GitHub Actions
# self-hosted runner (see .github/workflows/deploy.yml) with the commit SHA that
# passed CI as $1. Safe to re-run by hand: it converges the deployment clone to
# the target commit, rebuilds the venv, restarts the service, and health-checks.
# On a failed health check it rolls back to the previously deployed commit.
set -euo pipefail

DEPLOY_DIR="/home/pi/WeatherFrame/weather-frame"
SERVICE="weather-frame"
HEALTH_URL="http://localhost:8080/status"
HEALTH_TIMEOUT=30   # seconds to wait for the service to come back healthy

# The runner service starts with a minimal env, so uv (installed under
# ~/.local/bin) is not on PATH by default. Source its env shim if present.
if [ -f "$HOME/.local/bin/env" ]; then
    # shellcheck disable=SC1091
    . "$HOME/.local/bin/env"
fi

TARGET_SHA="${1:?usage: deploy.sh <commit-sha>}"

cd "$DEPLOY_DIR"

# Remember where we are so we can roll back if the new revision is unhealthy.
PREV_SHA="$(git rev-parse HEAD)"
echo "Deploying $TARGET_SHA (current: $PREV_SHA)"

# Wait for the service to report healthy (HTTP 200 from /status). Returns 0 on
# success, 1 if it never comes up within HEALTH_TIMEOUT.
wait_for_health() {
    local deadline=$(( SECONDS + HEALTH_TIMEOUT ))
    while [ "$SECONDS" -lt "$deadline" ]; do
        if curl -fsS -o /dev/null "$HEALTH_URL"; then
            return 0
        fi
        sleep 2
    done
    return 1
}

# Bring the deployment clone to an exact, clean state at TARGET_SHA. reset --hard
# discards any drift in the deploy clone -- config must come from env, never local
# edits to tracked files.
deploy_revision() {
    local sha="$1"
    git fetch origin main --quiet
    git reset --hard "$sha"
    uv sync --extra pi
    sudo systemctl restart "$SERVICE"
}

deploy_revision "$TARGET_SHA"

if wait_for_health; then
    echo "Deploy OK: $SERVICE healthy at $TARGET_SHA"
    exit 0
fi

echo "Health check failed after ${HEALTH_TIMEOUT}s -- rolling back to $PREV_SHA" >&2
deploy_revision "$PREV_SHA"

if wait_for_health; then
    echo "Rolled back to $PREV_SHA; service healthy on previous revision." >&2
else
    echo "WARNING: service still unhealthy after rollback to $PREV_SHA." >&2
fi
exit 1
