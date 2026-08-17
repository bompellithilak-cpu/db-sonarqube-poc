#!/usr/bin/env bash
# ===========================================================================
#  Deploy the DQ Framework to the Databricks PROD folder.
#  Invoked by .github/workflows/ci-cd.yml AFTER the quality gate has passed.
#
#  Required environment:
#    DATABRICKS_HOST   e.g. https://dbc-xxxxxxxx.cloud.databricks.com
#    DATABRICKS_TOKEN  personal access token or OAuth token
#    PROD_PATH         defaults to /Shared/PROD/DQ_Framework
# ===========================================================================
set -euo pipefail
# -e  stop on first error   -u  fail on unset variable
# -o pipefail  a failure anywhere in a pipe fails the whole pipe.
# Without pipefail, `cmd | tee log` reports success even when cmd failed.

PROD_PATH="${PROD_PATH:-/Shared/PROD/DQ_Framework}"

echo "==> Deploying to ${PROD_PATH} on ${DATABRICKS_HOST}"

# --- 1. Preflight ---------------------------------------------------------
# Confirm the token works before we start mutating the workspace.
databricks current-user me > /dev/null
echo "    authenticated OK"

# --- 2. Ensure the target exists -----------------------------------------
# mkdirs is idempotent: it succeeds whether or not the folder is already there.
databricks workspace mkdirs "${PROD_PATH}"

# --- 3. Import the source tree -------------------------------------------
# --overwrite  replace files that already exist (this is a redeploy, not a merge)
#
# NOTE: `workspace import-dir` uploads the WHOLE directory. We deploy src/ and
# notebooks/ only -- tests, CI config and docs have no business in PROD.
#
# It also has no --exclude flag, so we stage a copy and strip anything PROD
# must not receive. bad_examples/ holds the deliberate-violation template used
# for the failure demo; shipping fake credentials to PROD would undercut the
# very control this pipeline exists to demonstrate.
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

for DIR in src notebooks; do
  cp -r "${DIR}" "${STAGE}/${DIR}"
  done
  rm -rf "${STAGE}/src/bad_examples"
  find "${STAGE}" -name '*.template' -delete
  find "${STAGE}" -name '__pycache__' -type d -prune -exec rm -rf {} +

  for DIR in src notebooks; do
    echo "==> Importing ${DIR}/ -> ${PROD_PATH}/${DIR}"
      databricks workspace import-dir "${STAGE}/${DIR}" "${PROD_PATH}/${DIR}" --overwrite
      done

      # --- 4. Ship the check catalogue -----------------------------------------
      # checks.yaml is configuration, not code, but PROD needs it to run.
      # `workspace import` takes the TARGET path as its only positional argument;
      # the local file is passed with --file. Reversing these is a common trip-up.
      databricks workspace import "${PROD_PATH}/checks.yaml" \
        --file checks.yaml --format AUTO --overwrite

        # --- 5. Verify ------------------------------------------------------------
        # A deploy that reports success without confirming what landed is a deploy
        # you cannot trust. List the target so the log shows exactly what is there.
        echo "==> Contents of ${PROD_PATH}:"
        databricks workspace list "${PROD_PATH}" --output json

        echo "==> Deployment complete."
        
