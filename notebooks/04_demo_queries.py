# Databricks notebook source
"""Demo queries for hackathon storytelling and agentic exploration."""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

sys.path.append(str(Path.cwd() / "src"))

from hackathon_2026.spark_helpers import table_name  # noqa: E402

dbutils.widgets.text("catalog", "hackathon")
dbutils.widgets.text("schema", "virtue_foundation")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")


underserved = spark.table(table_name(catalog, schema, "gold_underserved_district_candidates"))
pincode_enrichment = spark.table(table_name(catalog, schema, "gold_pincode_health_enrichment"))
district_context = spark.table(table_name(catalog, schema, "gold_district_health_context"))

# COMMAND ----------

# Top districts where demand-side health burden appears high.
display(
    underserved.select(
        "state_name",
        "district_name",
        "demand_side_need_score",
        "health_insurance_percent",
        "institutional_delivery_percent",
        "women_anaemia_percent",
        "child_stunting_percent",
        "post_office_count",
        "data_caution",
    )
    .orderBy(F.desc("demand_side_need_score"))
    .limit(25)
)

# COMMAND ----------

# PIN codes that should not be joined directly because postal geography is ambiguous.
display(
    pincode_enrichment.select(
        "pincode",
        "post_office_count",
        "district_count",
        "state_count",
        "district_names",
        "state_names",
        "match_status",
    )
    .where(F.col("match_status") == "ambiguous_pin_geography")
    .orderBy(F.desc("district_count"), F.desc("state_count"), F.desc("post_office_count"))
    .limit(50)
)

# COMMAND ----------

# Match-status distribution is a compact quality story for judges.
display(
    pincode_enrichment.groupBy("match_status").agg(F.count("*").alias("pincode_count")).orderBy(F.desc("pincode_count"))
)

# COMMAND ----------

# Districts with the most public-health indicator caution flags.
display(
    district_context.select(
        "state_name",
        "district_name",
        "suppressed_indicator_count",
        "low_sample_estimate_count",
        "pincode_count",
        "post_office_count",
    )
    .orderBy(F.desc("suppressed_indicator_count"), F.desc("low_sample_estimate_count"))
    .limit(25)
)

# COMMAND ----------

agent_prompt = """
You are a healthcare access planning assistant.

Use only the gold tables in this schema:
- gold_district_health_context
- gold_pincode_health_enrichment
- gold_underserved_district_candidates

Rules:
- Do not present PIN-derived district or state as exact when match_status is ambiguous_pin_geography.
- Treat suppressed NFHS values as unavailable, not zero.
- Mention low-sample estimate caution when low_sample_estimate_count is greater than zero.
- Prefer spatial joins from facility coordinates when facility latitude and longitude are available.

Task:
Identify three districts that may deserve deeper review for healthcare access planning.
Explain the evidence, data cautions, and the next validation step for each.
"""

print(agent_prompt)
