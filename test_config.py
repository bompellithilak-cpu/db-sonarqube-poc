"""Unit tests for the YAML check catalogue loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from dq_framework.config import DatasetConfig, load_config

VALID_YAML = """
datasets:
  - name: retail_orders
    source: samples.tpch.orders
    checks:
      - type: null_check
        columns: [o_orderkey]
      - type: record_count_check
        min_rows: 1
"""


def test_load_config_parses_datasets(tmp_path: Path):
    path = tmp_path / "checks.yaml"
    path.write_text(VALID_YAML)

    configs = load_config(path)

    assert len(configs) == 1
    assert configs[0].name == "retail_orders"
    assert configs[0].source == "samples.tpch.orders"
    assert len(configs[0].checks) == 2


def test_load_config_raises_when_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_raises_when_datasets_section_absent(tmp_path: Path):
    path = tmp_path / "checks.yaml"
    path.write_text("something_else: true\n")
    with pytest.raises(ValueError, match="No 'datasets' section"):
        load_config(path)


def test_load_config_raises_on_empty_file(tmp_path: Path):
    path = tmp_path / "checks.yaml"
    path.write_text("")
    with pytest.raises(ValueError):
        load_config(path)


def test_dataset_config_rejects_missing_keys():
    with pytest.raises(ValueError, match="missing required keys"):
        DatasetConfig.from_dict({"name": "x"})


def test_dataset_config_from_dict_roundtrip():
    payload = {"name": "n", "source": "s", "checks": [{"type": "null_check"}]}
    config = DatasetConfig.from_dict(payload)
    assert (config.name, config.source) == ("n", "s")
