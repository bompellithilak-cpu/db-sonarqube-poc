"""Shared pytest fixtures.

A single local SparkSession is created for the whole test session --
building one per test would dominate the runtime and make the CI job slow
enough that people start skipping it.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from pyspark.sql import SparkSession

# CI containers frequently have a hostname that does not resolve, which makes
# the Spark driver fail to start with UnknownHostException. Binding explicitly
# to loopback removes the dependency on name resolution entirely.
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.appName("dq-framework-tests")
        .master("local[2]")
        # Small shuffle partition count: the default 200 creates hundreds of
        # empty tasks on tiny test data and slows the suite considerably.
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def orders_df(spark: SparkSession):
    """A small orders dataset with one seeded defect of each kind."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [
        ("O001", "C001", 19.99, now - timedelta(hours=1)),
        ("O002", "C002", 49.50, now - timedelta(hours=2)),
        ("O003", "C003", 9.25, now - timedelta(hours=3)),
        ("O003", "C004", 15.00, now - timedelta(hours=4)),   # duplicate order_id
        ("O005", None, 22.00, now - timedelta(hours=5)),     # null customer_id
    ]
    return spark.createDataFrame(rows, ["order_id", "customer_id", "amount", "order_ts"])
