"""Unit tests for the check runner and scorecard aggregation."""
from __future__ import annotations

from dq_framework import runner
from dq_framework.models import CheckStatus


def test_runner_executes_configured_checks(orders_df):
    specs = [
        {"type": "null_check", "columns": ["customer_id"]},
        {"type": "duplicate_check", "key_columns": ["order_id"]},
        {"type": "record_count_check", "min_rows": 1},
    ]
    results = runner.run_checks(orders_df, specs)
    assert len(results) == 3
    assert [r.dimension for r in results] == ["completeness", "uniqueness", "volume"]


def test_runner_records_unknown_check_type_as_errored(orders_df):
    results = runner.run_checks(orders_df, [{"type": "not_a_real_check"}])
    assert results[0].status is CheckStatus.ERRORED
    assert "Unknown check type" in results[0].details["error"]


def test_runner_converts_bad_params_into_errored(orders_df):
    results = runner.run_checks(orders_df, [{"type": "null_check", "columns": ["nope"]}])
    assert results[0].status is CheckStatus.ERRORED
    assert "ValueError" in results[0].details["error"]


def test_runner_continues_after_a_failing_check(orders_df):
    specs = [
        {"type": "null_check", "columns": ["nope"]},        # errors
        {"type": "record_count_check", "min_rows": 1},      # still runs
    ]
    results = runner.run_checks(orders_df, specs)
    assert results[0].status is CheckStatus.ERRORED
    assert results[1].status is CheckStatus.PASSED


def test_summarise_marks_overall_failed_when_any_check_fails(orders_df):
    specs = [{"type": "null_check", "columns": ["customer_id"]}]
    summary = runner.summarise(runner.run_checks(orders_df, specs))
    assert summary["overall_passed"] is False
    assert summary["failed"] == 1


def test_summarise_marks_overall_failed_when_a_check_errors(orders_df):
    summary = runner.summarise(runner.run_checks(orders_df, [{"type": "bogus"}]))
    # An unrunnable check must never be reported as good quality.
    assert summary["overall_passed"] is False
    assert summary["errored"] == 1


def test_summarise_passes_when_everything_passes(orders_df):
    specs = [{"type": "record_count_check", "min_rows": 1, "max_rows": 100}]
    summary = runner.summarise(runner.run_checks(orders_df, specs))
    assert summary["overall_passed"] is True
    assert summary["total_checks"] == 1
