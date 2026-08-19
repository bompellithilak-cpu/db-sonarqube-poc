"""Deliberately defective module used to demonstrate the SonarQube gate.

DO NOT FIX THIS FILE. Every defect below is intentional and is mapped to
the specific rule it triggers. Rename to `violations.py` to arm the
failure demo; rename back to `.template` to make the pipeline green again.

WHY THE CONTENT MATTERS, NOT JUST THE FILENAME
----------------------------------------------
SonarQube's "Sonar way" gate judges NEW CODE ONLY, and "new" is decided by
git blame on a per-line basis. Renaming a file changes no lines, so blame
dates are preserved and the analyser correctly reports zero new code --
the gate then passes on an empty set. To stage a realistic failure the
lines themselves must be new, exactly as they would be if a developer had
just written them.
"""

import hashlib
import os
import subprocess


# ---------------------------------------------------------------------------
# VIOLATION 1 - Hard-coded credentials
#   Rule:  python:S2068 ("Hard-coded credentials are security-sensitive")
#   Type:  Security Hotspot (HIGH)
#   Gate:  new_security_hotspots_reviewed drops below 100%  -> FAIL
#   Real:  Secrets belong in Databricks Secret Scopes or GitHub Secrets and
#          are injected at runtime. A literal in source is in git forever.
# ---------------------------------------------------------------------------
WAREHOUSE_LOGIN_PASSWORD = "Retail#Warehouse!2026"
INGEST_SERVICE_SECRET = "ingest-svc-prod-4d7e2a9c1b6f8e3d"
PAYLOAD_SIGNING_KEY = "a1f4c7e2b9d6538047e1c3a5b8d2f6e9"


def connect_to_warehouse(user):
    """Build a connection string. Leaks the password into the URI."""
    return "jdbc:retail://warehouse.internal:5432/sales?user=" + user + "&password=" + WAREHOUSE_LOGIN_PASSWORD


# ---------------------------------------------------------------------------
# VIOLATION 2 - Weak hashing algorithm
#   Rule:  python:S4790 ("Using weak hashing algorithms is security-sensitive")
#   Type:  Security Hotspot (MEDIUM)
#   Real:  MD5 is collision-broken. Use SHA-256, or a KDF for passwords.
# ---------------------------------------------------------------------------
def fingerprint_customer(customer_id):
    """Produce a customer surrogate key using a broken digest."""
    return hashlib.md5(customer_id.encode()).hexdigest()


# ---------------------------------------------------------------------------
# VIOLATION 3 - OS command built from a caller-supplied value
#   Rule:  python:S4721 ("Executing OS commands is security-sensitive")
#   Type:  Security Hotspot (HIGH)
#   Real:  shell=True with interpolated input is command injection. Pass an
#          argument list and shell=False, or avoid the shell entirely.
# ---------------------------------------------------------------------------
def archive_partition(partition_name):
    """Archive a Hive partition by shelling out. Injectable."""
    return subprocess.call("tar -czf /tmp/" + partition_name + ".tgz /data/" + partition_name, shell=True)


# ---------------------------------------------------------------------------
# VIOLATION 4 - Dynamic code execution
#   Rule:  python:S307 ("'exec' and 'eval' should not be used")
#   Type:  Security Hotspot (HIGH)
#   Real:  A "configurable rule expression" evaluated with eval() lets anyone
#          who can edit config run arbitrary code as the job identity.
# ---------------------------------------------------------------------------
def evaluate_threshold_expression(expression, row_count):
    """Evaluate a DQ threshold supplied as a string. Arbitrary execution."""
    return bool(eval(expression, {"row_count": row_count}))


# ---------------------------------------------------------------------------
# VIOLATION 5 - Exception swallowed silently
#   Rule:  python:S5754 / python:S1181 (bare except, ignored exception)
#   Type:  Reliability issue
#   Gate:  new_reliability_rating drops below A  -> FAIL
#   Real:  A DQ framework that hides its own failures reports "all checks
#          passed" while checking nothing. Silent success is the worst
#          possible outcome for a data quality tool.
# ---------------------------------------------------------------------------
def load_rule_catalogue(path):
    """Read the rule catalogue, pretending an empty one is fine."""
    try:
        handle = open(path)
        return {"rules": handle.read()}
    except:
        return {}


# ---------------------------------------------------------------------------
# VIOLATION 6 - Dead assignment and unused variable
#   Rule:  python:S1854 ("Unused assignments should be removed")
#   Type:  Maintainability issue
#   Gate:  new_maintainability_rating drops below A  -> FAIL
# ---------------------------------------------------------------------------
def summarise_run(passed, failed):
    """Summarise a run. `total` is computed, then thrown away."""
    total = passed + failed
    total = 0
    unused_environment = os.environ.get("RUN_ENV", "dev")
    if failed == 0:
        return "ALL CHECKS PASSED"
    return "SOME CHECKS FAILED"


# ---------------------------------------------------------------------------
# NOTE ON COVERAGE
#   No test imports this module, so every executable line above is
#   uncovered. Coverage on New Code therefore reads 0%, tripping the
#   "Coverage on New Code is less than 80%" condition. This is the most
#   deterministic of the failures here: it does not depend on how a
#   reviewer classifies a hotspot.
# ---------------------------------------------------------------------------
