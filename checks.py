"""The four core data quality checks, implemented against PySpark DataFrames.

Design notes
------------
* Every check has the same signature shape and returns a `CheckResult`, so
  the runner can treat them uniformly.
* Checks never raise on a data problem -- a data problem is a FAILED result.
  They only raise on a programming error (e.g. a column that does not exist),
  which the runner converts into ERRORED.
* `threshold` is the minimum acceptable pass rate, expressed 0.0-1.0.
  A threshold of 1.0 means "zero tolerance".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pyspark.sql import DataFrame, functions as F

from dq_framework.models import CheckResult, CheckStatus


def _require_columns(df: DataFrame, columns: list[str]) -> None:
    """Fail fast with a clear message when a configured column is absent.

    Without this the checks would fail deep inside Spark with an
    AnalysisException that does not name the check, making config typos
    expensive to diagnose.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"Columns {missing} not found in DataFrame. Available: {sorted(df.columns)}"
        )


def _status(failed_rows: int, total_rows: int, threshold: float) -> CheckStatus:
    """Convert a failure count into PASSED/FAILED against the threshold."""
    pass_rate = 1.0 if total_rows == 0 else (total_rows - failed_rows) / total_rows
    return CheckStatus.PASSED if pass_rate >= threshold else CheckStatus.FAILED


def null_check(
    df: DataFrame,
    columns: list[str],
    threshold: float = 1.0,
) -> CheckResult:
    """Completeness: the given columns must not be NULL or empty/whitespace.

    Treating a whitespace-only string as missing is deliberate. Upstream
    CSV and JDBC loads routinely deliver '' or ' ' where the source system
    meant NULL, and a completeness check that ignores that reports a
    quality score the business does not recognise.
    """
    _require_columns(df, columns)
    total_rows = df.count()

    condition = None
    for column in columns:
        col = F.col(column)
        # `trim` on a cast to string handles numeric and date columns safely.
        is_missing = col.isNull() | (F.trim(col.cast("string")) == F.lit(""))
        condition = is_missing if condition is None else (condition | is_missing)

    failed_rows = df.filter(condition).count() if condition is not None else 0

    return CheckResult(
        check_name=f"null_check[{','.join(columns)}]",
        dimension="completeness",
        status=_status(failed_rows, total_rows, threshold),
        total_rows=total_rows,
        failed_rows=failed_rows,
        threshold=threshold,
        details={"columns": columns},
    )


def duplicate_check(
    df: DataFrame,
    key_columns: list[str],
    threshold: float = 1.0,
) -> CheckResult:
    """Uniqueness: the key columns must identify at most one row each.

    `failed_rows` counts every row belonging to a duplicated key, not the
    number of surplus rows. If an id appears three times that is three
    failed rows, because all three are untrustworthy until a human decides
    which one is correct.
    """
    _require_columns(df, key_columns)
    total_rows = df.count()

    duplicate_keys = (
        df.groupBy(*key_columns)
        .agg(F.count(F.lit(1)).alias("_occurrences"))
        .filter(F.col("_occurrences") > 1)
    )
    failed_rows = (
        duplicate_keys.agg(F.coalesce(F.sum("_occurrences"), F.lit(0))).collect()[0][0]
    )
    distinct_duplicated_keys = duplicate_keys.count()

    return CheckResult(
        check_name=f"duplicate_check[{','.join(key_columns)}]",
        dimension="uniqueness",
        status=_status(int(failed_rows), total_rows, threshold),
        total_rows=total_rows,
        failed_rows=int(failed_rows),
        threshold=threshold,
        details={
            "key_columns": key_columns,
            "distinct_duplicated_keys": distinct_duplicated_keys,
        },
    )


def record_count_check(
    df: DataFrame,
    min_rows: int,
    max_rows: int | None = None,
) -> CheckResult:
    """Volume: the row count must fall inside an expected range.

    This is the check that catches the failure mode nothing else does --
    a load that succeeds technically but delivers a fraction of the
    expected data. An empty DataFrame passes every row-level check
    trivially, so without a volume floor a silent upstream outage looks
    like perfect quality.
    """
    total_rows = df.count()

    too_few = total_rows < min_rows
    too_many = max_rows is not None and total_rows > max_rows
    breached = too_few or too_many

    return CheckResult(
        check_name="record_count_check",
        dimension="volume",
        # Volume is a dataset-level property, so it is pass/fail outright
        # rather than a proportion of rows.
        status=CheckStatus.FAILED if breached else CheckStatus.PASSED,
        total_rows=total_rows,
        failed_rows=total_rows if breached else 0,
        threshold=1.0,
        details={
            "min_rows": min_rows,
            "max_rows": max_rows,
            "breach": "too_few" if too_few else ("too_many" if too_many else None),
        },
    )


def freshness_check(
    df: DataFrame,
    timestamp_column: str,
    max_age_hours: int,
    as_of: datetime | None = None,
) -> CheckResult:
    """Timeliness: the newest record must be recent enough.

    `as_of` is injectable so the check is deterministic under test.
    Defaulting to a timezone-aware UTC now() avoids `utcnow()`, which
    returns a naive datetime that only pretends to be UTC -- a genuine
    source of off-by-hours bugs, and something SonarQube flags.
    """
    _require_columns(df, [timestamp_column])
    total_rows = df.count()
    reference = as_of or datetime.now(timezone.utc)

    if total_rows == 0:
        return CheckResult(
            check_name=f"freshness_check[{timestamp_column}]",
            dimension="timeliness",
            status=CheckStatus.FAILED,
            total_rows=0,
            failed_rows=0,
            threshold=1.0,
            details={"reason": "no rows to assess freshness"},
        )

    latest = df.agg(F.max(F.col(timestamp_column)).alias("_latest")).collect()[0][0]
    if latest is None:
        return CheckResult(
            check_name=f"freshness_check[{timestamp_column}]",
            dimension="timeliness",
            status=CheckStatus.FAILED,
            total_rows=total_rows,
            failed_rows=total_rows,
            threshold=1.0,
            details={"reason": f"all values in {timestamp_column} are NULL"},
        )

    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)

    age = reference - latest
    is_stale = age > timedelta(hours=max_age_hours)

    return CheckResult(
        check_name=f"freshness_check[{timestamp_column}]",
        dimension="timeliness",
        status=CheckStatus.FAILED if is_stale else CheckStatus.PASSED,
        total_rows=total_rows,
        failed_rows=total_rows if is_stale else 0,
        threshold=1.0,
        details={
            "timestamp_column": timestamp_column,
            "latest_record": latest.isoformat(),
            "age_hours": round(age.total_seconds() / 3600, 2),
            "max_age_hours": max_age_hours,
        },
    )
