#!/usr/bin/env bash
# ===========================================================================
#  Emergency rollback: redeploy PROD from a known-good git tag or commit.
#
#  Usage:  bash deploy/rollback.sh v1.0.3
#
#  Rolling back by re-running the bundle deploy at an older commit is safer
#  than hand-editing PROD, because the rolled-back state still matches
#  something in git that you can inspect later — and because it goes through
#  `databricks bundle deploy`, the rollback also reconciles the deployed Job
#  resource (schedule, permissions, tasks) back to that commit's definition,
#  not just the notebook files.
# ===========================================================================
set -euo pipefail

REF="${1:?Usage: rollback.sh <git-tag-or-sha>}"

echo "==> Rolling PROD back to ${REF}"
git fetch --all --tags
git checkout "${REF}"

databricks bundle validate -t prod
databricks bundle deploy -t prod

echo "==> Rollback complete. PROD now matches ${REF}."
echo "    Remember to fix forward on main -- this checkout is detached."
