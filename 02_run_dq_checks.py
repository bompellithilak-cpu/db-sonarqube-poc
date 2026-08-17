# Databricks notebook source
# MAGIC %md
# MAGIC # DQ Framework — Scheduled Runner (PROD entry point)
# MAGIC
# MAGIC This is the notebook a Databricks **Job** points at in production. It is
# MAGIC deployed to `/Shared/PROD/DQ_Framework/notebooks/` by GitHub Actions,
# MAGIC only after the SonarQube quality gate has passed.
# MAGIC
# MAGIC It is intentionally thin: load config, run checks, persist the scorecard,
# MAGIC fail the job if quality is unacceptable. All logic lives in `src/`, where
# MAGIC it is unit-tested and scanned.

# COMMAND ----------
dbutils.widgets.text("config_path", "checks.yaml")
dbutils.widgets.text("results_table", "main.default.dq_results")
# fail_job_on_error lets you run in observe-only mode during onboarding, then
# switch to enforcing once teams have cleaned up their data.
dbutils.widgets.dropdown("fail_job_on_error", "true", ["true", "false"])

config_path = dbutils.widgets.get("config_path")
results_table = dbutils.widgets.get("results_table")
fail_job = dbutils.widgets.get("fail_job_on_error") == "true"

# COMMAND ----------
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path.cwd().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from dq_framework import runner              # noqa: E402
from dq_framework.config import load_config  # noqa: E402

# COMMAND ----------
run_started_at = datetime.now(timezone.utc)
datasets = load_config(REPO_ROOT / config_path)
print(f"Loaded {len(datasets)} dataset(s) from {config_path}")

all_rows = []
overall_passed = True

for dataset in datasets:
    print(f"\n=== {dataset.name} ({dataset.source}) ===")
    df = spark.read.table(dataset.source)
    summary = runner.summarise(runner.run_checks(df, dataset.checks))

    for item in summary["results"]:
        print(f"  [{item['status']:>7}] {item['check_name']} "
              f"pass_rate={item['pass_rate']:.2%}")
        all_rows.append({
            "run_ts": run_started_at,
            "dataset": dataset.name,
            "source": dataset.source,
            **{k: v for k, v in item.items() if k != "details"},
            "details": str(item.get("details")),
        })

    overall_passed = overall_passed and summary["overall_passed"]

# COMMAND ----------
# MAGIC %md ## Persist the scorecard
# MAGIC Results are appended, never overwritten — the trend over time is the
# MAGIC point. A single snapshot tells you nothing about whether quality is
# MAGIC improving or degrading.

# COMMAND ----------
if all_rows:
    (spark.createDataFrame(all_rows)
        .write.mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(results_table))
    print(f"Wrote {len(all_rows)} result rows to {results_table}")

# COMMAND ----------
# MAGIC %md ## Enforce
# MAGIC Raising here is what makes the check meaningful: the Databricks Job goes
# MAGIC red, alerting fires, and downstream tasks that depend on this one do not
# MAGIC run on data we already know is bad.

# COMMAND ----------
if not overall_passed and fail_job:
    raise ValueError(
        "Data quality checks FAILED. Downstream processing halted. "
        f"See {results_table} for the failing checks."
    )

print("All data quality checks passed.")
