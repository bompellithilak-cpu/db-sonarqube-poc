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

# Demo: this edit was made in the Databricks Git folder and pushed from here.

import hashlib  # Needed for fingerprint_customer


def fingerprint_customer(customer_id):
    """Produce a customer surrogate key using a broken digest."""
    return hashlib.md5(customer_id.encode()).hexdigest()


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
