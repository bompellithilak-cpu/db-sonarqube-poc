"""Unit tests for the four core checks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dq_framework import checks
from dq_framework.models import CheckStatus


def test_null_check_detects_missing_customer_id(orders_df):
    result = checks.null_check(orders_df, ["customer_id"])
    assert result.status is CheckStatus.FAILED
    assert result.failed_rows == 1
    assert result.total_rows == 5


def test_null_check_passes_on_complete_column(orders_df):
    result = checks.null_check(orders_df, ["order_id"])
    assert result.status is CheckStatus.PASSED
    assert result.failed_rows == 0


def test_null_check_treats_blank_string_as_missing(spark):
    df = spark.createDataFrame([("A",), ("   ",), ("",)], ["code"])
    result = checks.null_check(df, ["code"])
    assert result.failed_rows == 2


def test_null_check_raises_on_unknown_column(orders_df):
    try:
        checks.null_check(orders_df, ["does_not_exist"])
    except ValueError as exc:
        assert "does_not_exist" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown column")


def test_duplicate_check_counts_all_rows_of_duplicated_key(orders_df):
    result = checks.duplicate_check(orders_df, ["order_id"])
    assert result.status is CheckStatus.FAILED
    # O003 appears twice, so both rows are untrustworthy.
    assert result.failed_rows == 2
    assert result.details["distinct_duplicated_keys"] == 1


def test_duplicate_check_passes_on_unique_key(spark):
    df = spark.createDataFrame([("A",), ("B",), ("C",)], ["id"])
    result = checks.duplicate_check(df, ["id"])
    assert result.status is CheckStatus.PASSED
    assert result.failed_rows == 0


def test_record_count_check_flags_under_volume(orders_df):
    result = checks.record_count_check(orders_df, min_rows=100)
    assert result.status is CheckStatus.FAILED
    assert result.details["breach"] == "too_few"


def test_record_count_check_flags_over_volume(orders_df):
    result = checks.record_count_check(orders_df, min_rows=1, max_rows=3)
    assert result.status is CheckStatus.FAILED
    assert result.details["breach"] == "too_many"


def test_record_count_check_passes_inside_range(orders_df):
    result = checks.record_count_check(orders_df, min_rows=1, max_rows=10)
    assert result.status is CheckStatus.PASSED


def test_freshness_check_passes_for_recent_data(orders_df):
    result = checks.freshness_check(orders_df, "order_ts", max_age_hours=24)
    assert result.status is CheckStatus.PASSED


def test_freshness_check_flags_stale_data(orders_df):
    future = datetime.now(timezone.utc) + timedelta(days=10)
    result = checks.freshness_check(orders_df, "order_ts", max_age_hours=24, as_of=future)
    assert result.status is CheckStatus.FAILED
    assert result.details["age_hours"] > 24


def test_freshness_check_fails_on_empty_dataset(spark):
    empty = spark.createDataFrame([], "order_ts timestamp")
    result = checks.freshness_check(empty, "order_ts", max_age_hours=24)
    assert result.status is CheckStatus.FAILED
    assert "no rows" in result.details["reason"]


def test_pass_rate_of_empty_dataset_is_one(spark):
    empty = spark.createDataFrame([], "id string")
    result = checks.null_check(empty, ["id"])
    assert result.pass_rate == 1.0
