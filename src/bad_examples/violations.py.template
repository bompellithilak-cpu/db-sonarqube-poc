"""Deliberately defective module used to demonstrate the SonarQube gate.

DO NOT FIX THIS FILE. Every defect below is intentional and is mapped to
the specific rule it triggers. Rename to `violations.py` to arm the
failure demo; delete it to make the pipeline green again.
"""
import hashlib
import os

# ---------------------------------------------------------------------------
# VIOLATION 1 — Hardcoded credentials
# Rule:     python:S2068 ("Hard-coded credentials are security-sensitive")
# Type:     Security Hotspot (HIGH)
# Gate:     new_security_hotspots_reviewed drops below 100%  -> FAIL
# Why:      Credentials in source are readable by anyone with repo access,
#           survive in git history forever, and cannot be rotated centrally.
#
# NOTE ON THE VALUES BELOW
# These are deliberately generic strings, NOT real provider key formats.
# An earlier version used an AWS-shaped key (AKIA...) and GitHub push
# protection blocked the commit outright -- which is itself a useful lesson:
# secret scanning at the push boundary is a SEPARATE control that fires
# before SonarQube ever runs. For this demo we need the commit to land so the
# quality gate can be the thing that stops it, so we use credentials that
# Sonar flags but GitHub's provider-pattern scanner does not.
# ---------------------------------------------------------------------------
DATABASE_PASSWORD = "Pr0dRetail2026Secret"
SERVICE_ACCOUNT_TOKEN = "svc-retail-dq-prod-9f3c1a7b8e2d4f6a"
ENCRYPTION_SECRET_KEY = "b5c9d8e7f1a2b3c4d5e6f70a1b2c3d4e"


# ---------------------------------------------------------------------------
# VIOLATION 2 — Weak hashing algorithm
# Rule:     python:S4790 ("Using weak hashing algorithms is security-sensitive")
# Type:     Security Hotspot
# Gate:     new_security_hotspots_reviewed < 100%             -> FAIL
# Why:      MD5 is collision-broken and unsuitable for anything security
#           related, including "just" fingerprinting records that are later
#           trusted for deduplication.
# ---------------------------------------------------------------------------
def fingerprint_record(payload: str) -> str:
    return hashlib.md5(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# VIOLATION 3 — Unused local variable
# Rule:     python:S1481 ("Unused local variables should be removed")
# Type:     Code Smell (MINOR)
# Gate:     contributes to new_maintainability_rating
# Why:      Usually the residue of a half-finished change; frequently hides
#           a real bug where the computed value was meant to be used.
# ---------------------------------------------------------------------------
def compute_totals(orders):
    total_value = 0
    unused_discount_rate = 0.15          # never referenced
    for order in orders:
        total_value += order["amount"]
    return total_value


# ---------------------------------------------------------------------------
# VIOLATION 4 — Duplicated code block
# Rule:     common-py:DuplicatedBlocks
# Type:     Code Smell
# Gate:     new_duplicated_lines_density > 3%                 -> FAIL
# Why:      A fix applied to one copy and not the other is the single most
#           common source of "we already fixed that" defects.
# ---------------------------------------------------------------------------
def validate_orders_north(orders):
    valid = []
    for order in orders:
        if order.get("amount") is None:
            continue
        if order["amount"] <= 0:
            continue
        if order.get("customer_id") is None:
            continue
        if order.get("order_date") is None:
            continue
        valid.append(order)
    return valid


def validate_orders_south(orders):
    valid = []
    for order in orders:
        if order.get("amount") is None:
            continue
        if order["amount"] <= 0:
            continue
        if order.get("customer_id") is None:
            continue
        if order.get("order_date") is None:
            continue
        valid.append(order)
    return valid


# ---------------------------------------------------------------------------
# VIOLATION 5 — Bare except swallowing every error
# Rule:     python:S5754 / python:S112
# Type:     Code Smell (CRITICAL) — reliability impact
# Gate:     contributes to new_reliability_rating              -> FAIL
# Why:      Catching everything and returning a default turns a loud failure
#           into a silent wrong answer. In a DQ framework that means
#           reporting "quality is fine" when the check never ran.
# ---------------------------------------------------------------------------
def load_threshold(path):
    try:
        with open(path) as handle:
            return float(handle.read())
    except:                              # noqa: E722
        return 0.0


# ---------------------------------------------------------------------------
# VIOLATION 6 — Command injection via unsanitised input
# Rule:     python:S4721 ("Executing OS commands is security-sensitive")
# Type:     Security Hotspot / Vulnerability
# Gate:     new_security_rating below A                        -> FAIL
# Why:      Any caller-controlled value reaching a shell is a remote code
#           execution path.
# ---------------------------------------------------------------------------
def archive_partition(partition_name):
    os.system("tar -czf /tmp/archive.tgz /data/" + partition_name)
