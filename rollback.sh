#!/usr/bin/env bash
# ===========================================================================
#  Emergency rollback: redeploy PROD from a known-good git tag or commit.
#
#  Usage:  bash deploy/rollback.sh v1.0.3
#
#  Rolling back by re-running the pipeline at an older commit is safer than
#  hand-editing PROD, because the rolled-back state still matches something
#  in git that you can inspect later.
# ===========================================================================
set -euo pipefail

REF="${1:?Usage: rollback.sh <git-tag-or-sha>}"
PROD_PATH="${PROD_PATH:-/Shared/PROD/DQ_Framework}"

echo "==> Rolling ${PROD_PATH} back to ${REF}"
git fetch --all --tags
git checkout "${REF}"

bash deploy/deploy_to_prod.sh

echo "==> Rollback complete. PROD now matches ${REF}."
echo "    Remember to fix forward on main -- this checkout is detached."
