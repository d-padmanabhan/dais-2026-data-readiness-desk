# Databricks notebook source
"""Build gold tables for enrichment and demo-friendly district analysis."""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

sys.path.append(str(Path.cwd() / "src"))

from hackathon_2026.spark_helpers import require_columns, table_name, write_delta  # noqa: E402

dbutils.widgets.text("catalog", "hackathon")
dbutils.widgets.text("schema", "virtue_foundation")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")


def find_metric(columns: list[str], include_terms: list[str], exclude_terms: list[str] | None = None) -> str | None:
    """Find a likely NFHS metric by normalized column-name terms.

    Args:
        columns: Available dataframe column names.
        include_terms: Terms that must all appear in the column name.
        exclude_terms: Terms that must not appear in the column name.

    Returns:
        First matching column name, or None when no matching metric exists.
    """
    exclude_terms = exclude_terms or []
    for column in columns:
        if all(term in column for term in include_terms) and not any(term in column for term in exclude_terms):
            return column
    return None


def metric_or_null(df: DataFrame, column: str | None, alias: str) -> Column:
    """Return a metric column when present or a typed null placeholder.

    Args:
        df: Dataframe containing optional metric columns.
        column: Candidate metric column name.
        alias: Output alias.

    Returns:
        Spark column expression for the metric.
    """
    if column and column in df.columns:
        return F.col(column).cast("double").alias(alias)
    return F.lit(None).cast("double").alias(alias)


pincode_lookup = spark.table(table_name(catalog, schema, "silver_pincode_lookup"))
pincode_offices = spark.table(table_name(catalog, schema, "silver_pincode_post_offices"))
nfhs = spark.table(table_name(catalog, schema, "silver_nfhs5_district_health_indicators"))

require_columns(
    pincode_lookup,
    {"is_geography_ambiguous", "pincode", "representative_district_normalized", "representative_state_normalized"},
    "silver_pincode_lookup",
)
require_columns(
    pincode_offices,
    {"district_normalized", "has_coordinates", "pincode", "state_normalized"},
    "silver_pincode_post_offices",
)
require_columns(
    nfhs,
    {"district_name", "district_normalized", "state_name", "state_normalized"},
    "silver_nfhs5_district_health_indicators",
)

district_postal_summary = (
    pincode_offices.groupBy("state_normalized", "district_normalized")
    .agg(
        F.countDistinct("pincode").alias("pincode_count"),
        F.count("*").alias("post_office_count"),
        F.sum(F.col("has_coordinates").cast("int")).alias("geocoded_post_office_count"),
    )
    .withColumn(
        "geocoded_post_office_ratio",
        F.when(F.col("post_office_count") > 0, F.col("geocoded_post_office_count") / F.col("post_office_count")),
    )
)

district_health_context = (
    nfhs.join(district_postal_summary, on=["state_normalized", "district_normalized"], how="left")
    .withColumn("pincode_count", F.coalesce(F.col("pincode_count"), F.lit(0)))
    .withColumn("post_office_count", F.coalesce(F.col("post_office_count"), F.lit(0)))
    .withColumn("geocoded_post_office_count", F.coalesce(F.col("geocoded_post_office_count"), F.lit(0)))
)

nfhs_prefixed = nfhs.select(
    "state_normalized",
    "district_normalized",
    *[
        F.col(column).alias(f"nfhs_{column}")
        for column in nfhs.columns
        if column not in {"state_normalized", "district_normalized"}
    ],
)

pincode_enrichment = (
    pincode_lookup.join(
        nfhs_prefixed,
        (pincode_lookup.representative_state_normalized == nfhs_prefixed.state_normalized)
        & (pincode_lookup.representative_district_normalized == nfhs_prefixed.district_normalized),
        how="left",
    )
    .drop(nfhs_prefixed.state_normalized)
    .drop(nfhs_prefixed.district_normalized)
    .withColumn(
        "match_status",
        F.when(F.col("is_geography_ambiguous"), F.lit("ambiguous_pin_geography"))
        .when(F.col("representative_district_normalized").isNull(), F.lit("no_representative_district"))
        .when(F.col("nfhs_district_name").isNull(), F.lit("unmatched_nfhs_district"))
        .otherwise(F.lit("matched")),
    )
)

columns = district_health_context.columns
health_insurance_col = find_metric(columns, ["health", "insurance"])
institutional_delivery_col = find_metric(columns, ["institutional"], ["caesarean", "c_section"])
women_anaemia_col = find_metric(columns, ["women", "anaemic"])
child_stunting_col = find_metric(columns, ["stunted"])

planning_metrics = district_health_context.select(
    "state_name",
    "district_name",
    "state_normalized",
    "district_normalized",
    "pincode_count",
    "post_office_count",
    "geocoded_post_office_ratio",
    "suppressed_indicator_count",
    "low_sample_estimate_count",
    metric_or_null(district_health_context, health_insurance_col, "health_insurance_percent"),
    metric_or_null(district_health_context, institutional_delivery_col, "institutional_delivery_percent"),
    metric_or_null(district_health_context, women_anaemia_col, "women_anaemia_percent"),
    metric_or_null(district_health_context, child_stunting_col, "child_stunting_percent"),
)

underserved_candidates = planning_metrics.withColumn(
    "demand_side_need_score",
    F.coalesce(F.col("women_anaemia_percent"), F.lit(0.0))
    + F.coalesce(F.col("child_stunting_percent"), F.lit(0.0))
    + (100.0 - F.coalesce(F.col("health_insurance_percent"), F.lit(100.0)))
    + (100.0 - F.coalesce(F.col("institutional_delivery_percent"), F.lit(100.0))),
).withColumn(
    "data_caution",
    F.when(
        (F.col("suppressed_indicator_count") > 0) | (F.col("low_sample_estimate_count") > 0),
        F.lit("review_suppressed_or_low_sample_indicators"),
    ).otherwise(F.lit("standard")),
)

write_delta(district_health_context, catalog, schema, "gold_district_health_context")
write_delta(pincode_enrichment, catalog, schema, "gold_pincode_health_enrichment")
write_delta(underserved_candidates, catalog, schema, "gold_underserved_district_candidates")

display(underserved_candidates.orderBy(F.desc("demand_side_need_score")).limit(25))
