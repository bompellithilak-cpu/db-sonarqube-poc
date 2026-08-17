"""Result types shared by every check.

Every check returns the same shape so the runner can aggregate results
without knowing anything about the individual check that produced them.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    """Outcome of a single check.

    Inherits from `str` so the value serialises directly to JSON and
    compares cleanly against plain strings in tests.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    # Distinguished from FAILED so an infrastructure problem (missing table,
    # bad permissions) is never silently reported as a data quality problem.
    ERRORED = "ERRORED"


@dataclass
class CheckResult:
    """Outcome of one check against one dataset."""

    check_name: str
    dimension: str
    status: CheckStatus
    total_rows: int
    failed_rows: int
    threshold: float
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Fraction of rows that satisfied the check (1.0 when there is no data).

        An empty dataset scores 1.0 rather than 0.0 or NaN: "no bad rows"
        is the honest reading, and volume problems are caught by the
        record-count check instead.
        """
        if self.total_rows == 0:
            return 1.0
        return (self.total_rows - self.failed_rows) / self.total_rows

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["pass_rate"] = round(self.pass_rate, 4)
        return payload
