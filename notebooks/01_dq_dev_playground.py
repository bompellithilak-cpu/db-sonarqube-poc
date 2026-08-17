# Databricks notebook source
# MAGIC %md
# MAGIC # DQ Framework — Developer Playground
# MAGIC
# MAGIC Interactive notebook for **developing and trying out** checks against real
# MAGIC data before committing them.
# MAGIC
# MAGIC Runs from the Databricks Git folder at `/Workspace/Repos/<you>/db-sonarqube-poc`
# MAGIC (DEV). Nothing here is deployed to PROD by the pipeline except via git.

# COMMAND ----------
# MAGIC %md ## Make the framework importable
# MAGIC The repo root is the Git folder; `src/` holds the package. Adding it to
# MAGIC `sys.path` means we import exactly the code that CI tested — no wheel
# MAGIC build, no copy-paste drift between the notebook and the module.

# COMMAND ----------
import sys
from pathlib import Path

REPO_ROOT = Path.cwd().parent          # notebooks/ -> repo root
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

print(f"Repo root: {REPO_ROOT}")
print(f"Source on path: {SRC}")

# COMMAND ----------
from dq_framework import checks, runner          # noqa: E402
from dq_framework.config import load_config      # noqa: E402

# COMMAND ----------
# MAGIC %md ## Load a dataset
# MAGIC `samples.tpch.orders` ships with every Databricks workspace, so this
# MAGIC notebook runs for anyone without setting up source data first.

# COMMAND ----------
df = spark.read.table("samples.tpch.orders")
print(f"Loaded {df.count():,} rows")
display(df.limit(10))

# COMMAND ----------
# MAGIC %md ## Try individual checks

# COMMAND ----------
result = checks.null_check(df, ["o_orderkey", "o_custkey"])
print(result.to_dict())

# COMMAND ----------
result = checks.duplicate_check(df, ["o_orderkey"])
print(result.to_dict())

# COMMAND ----------
result = checks.record_count_check(df, min_rows=1000, max_rows=10_000_000)
print(result.to_dict())

# COMMAND ----------
# MAGIC %md ## Run the whole catalogue from config

# COMMAND ----------
datasets = load_config(REPO_ROOT / "checks.yaml")
dataset = datasets[0]

source_df = spark.read.table(dataset.source)
summary = runner.summarise(runner.run_checks(source_df, dataset.checks))

print(f"Overall passed: {summary['overall_passed']}")
print(f"{summary['passed']} passed / {summary['failed']} failed / {summary['errored']} errored")
display(spark.createDataFrame(summary["results"]))
