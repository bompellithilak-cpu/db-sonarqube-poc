# Demo: this edit was made in the Databricks Git folder and pushed from here.

#--------------------
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


"""Declarative check configuration, loaded from YAML.

Keeping the check catalogue in YAML rather than code means a data steward
can add a rule without a Python change -- and, importantly for this POC,
that a config change still goes through the same PR + SonarQube + deploy
pipeline as everything else.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DatasetConfig:
    """Everything the runner needs to assess one dataset."""

    name: str
    source: str
    checks: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetConfig":
        missing = [k for k in ("name", "source", "checks") if k not in payload]
        if missing:
            raise ValueError(f"Dataset config is missing required keys: {missing}")
        return cls(
            name=payload["name"],
            source=payload["source"],
            checks=payload["checks"],
        )


def load_config(path: str | Path) -> list[DatasetConfig]:
    """Read and validate the YAML check catalogue.

    Validation happens at load time rather than at check time so a typo in
    the config fails immediately, before any Spark work is done.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Check config not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text()) or {}
    datasets = raw.get("datasets")
    if not datasets:
        raise ValueError(f"No 'datasets' section found in {config_path}")

    return [DatasetConfig.from_dict(entry) for entry in datasets]
