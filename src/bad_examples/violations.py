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
# 