"""Executes a configured set of checks and aggregates the results.

The runner is deliberately thin: it dispatches to the check functions,
converts unexpected exceptions into ERRORED results, and decides the
overall verdict. All quality logic lives in `checks.py`.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from pyspark.sql import DataFrame

from dq_framework import checks
from dq_framework.models import CheckResult, CheckStatus

logger = logging.getLogger(__name__)

# Mapping from the `type` key in YAML to the function that implements it.
# A registry keeps `run_checks` free of a long if/elif chain and makes
# adding a check a one-line change.
CHECK_REGISTRY: dict[str, Callable[..., CheckResult]] = {
    "null_check": checks.null_check,
    "duplicate_check": checks.duplicate_check,
    "record_count_check": checks.record_count_check,
    "freshness_check": checks.freshness_check,
}


def run_checks(df: DataFrame, check_specs: list[dict[str, Any]]) -> list[CheckResult]:
    """Run every configured check against one DataFrame.

    A check that raises is recorded as ERRORED and execution continues, so
    one misconfigured rule cannot hide the results of every rule after it.
    """
    results: list[CheckResult] = []

    for spec in check_specs:
        check_type = spec.get("type")
        handler = CHECK_REGISTRY.get(check_type)

        if handler is None:
            results.append(
                CheckResult(
                    check_name=str(check_type),
                    dimension="unknown",
                    status=CheckStatus.ERRORED,
                    total_rows=0,
                    failed_rows=0,
                    threshold=0.0,
                    details={
                        "error": f"Unknown check type '{check_type}'",
                        "supported": sorted(CHECK_REGISTRY),
                    },
                )
            )
            continue

        params = {k: v for k, v in spec.items() if k != "type"}
        try:
            results.append(handler(df, **params))
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            logger.exception("Check %s failed to execute", check_type)
            results.append(
                CheckResult(
                    check_name=str(check_type),
                    dimension="unknown",
                    status=CheckStatus.ERRORED,
                    total_rows=0,
                    failed_rows=0,
                    threshold=0.0,
                    details={"error": f"{type(exc).__name__}: {exc}"},
                )
            )

    return results


def summarise(results: list[CheckResult]) -> dict[str, Any]:
    """Aggregate results into a scorecard.

    `overall_passed` is false if anything ERRORED as well as if anything
    FAILED. An unrunnable check is not evidence of good quality, and
    treating it as a pass is how monitoring quietly stops working.
    """
    passed = sum(1 for r in results if r.status is CheckStatus.PASSED)
    failed = sum(1 for r in results if r.status is CheckStatus.FAILED)
    errored = sum(1 for r in results if r.status is CheckStatus.ERRORED)

    return {
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "overall_passed": failed == 0 and errored == 0,
        "results": [r.to_dict() for r in results],
    }
