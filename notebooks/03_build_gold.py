# Databricks notebook source
"""Build gold tables for enrichment and demo-friendly district analysis."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

dbutils.widgets.text("catalog", "data_readiness_desk")
dbutils.widgets.text("schema", "pipeline")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")


def table_name(catalog_name: str, schema_name: str, table: str) -> str:
    """Return a quoted Unity Catalog table name."""
    return f"`{catalog_name}`.`{schema_name}`.`{table}`"


def require_columns(df: DataFrame, required_columns: set[str], dataset_name: str) -> None:
    """Fail fast when required columns are missing."""
    missing = sorted(required_columns.difference(df.columns))
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")


def write_delta(df: DataFrame, catalog_name: str, schema_name: str, table: str) -> None:
    """Overwrite a managed Delta table."""
    (
        df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .format("delta")
        .saveAsTable(table_name(catalog_name, schema_name, table))
    )


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
hmis_indicator_totals = spark.table(table_name(catalog, schema, "silver_hmis_2019_20_indicator_totals"))
facilities_geo = spark.table(table_name(catalog, schema, "silver_facilities_geo"))

require_columns(
    facilities_geo,
    {
        "source_state_name",
        "source_state_normalized",
        "has_valid_coordinates",
        "has_pincode",
        "has_capability_text",
        "care_substance_missing_count",
    },
    "silver_facilities_geo",
)

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
require_columns(
    hmis_indicator_totals,
    {"indicator_name", "state_name", "state_normalized", "value"},
    "silver_hmis_2019_20_indicator_totals",
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

hmis_state_pivot = (
    hmis_indicator_totals.groupBy("state_name", "state_normalized")
    .pivot("indicator_name")
    .agg(F.first("value", ignorenulls=True))
)

hmis_state_indicator_summary = (
    hmis_state_pivot.withColumn(
        "live_births",
        F.coalesce(F.col("live_birth_male"), F.lit(0)) + F.coalesce(F.col("live_birth_female"), F.lit(0)),
    )
    .withColumn(
        "fully_immunized_children",
        F.coalesce(F.col("fully_immunized_male"), F.lit(0)) + F.coalesce(F.col("fully_immunized_female"), F.lit(0)),
    )
    .withColumn(
        "anc_four_plus_rate_percent",
        F.when(F.col("anc_registered") > 0, F.col("anc_four_plus") / F.col("anc_registered") * 100.0),
    )
    .withColumn(
        "institutional_delivery_to_live_birth_ratio_percent",
        F.when(F.col("live_births") > 0, F.col("institutional_deliveries") / F.col("live_births") * 100.0),
    )
    .withColumn(
        "fully_immunized_to_live_birth_ratio_percent",
        F.when(F.col("live_births") > 0, F.col("fully_immunized_children") / F.col("live_births") * 100.0),
    )
    .withColumn("geo_grain", F.lit("state"))
    .withColumn("data_caution", F.lit("state_grain_hmis_fallback_not_district_reconciliation"))
)

facility_verdicts = (
    facilities_geo.groupBy("source_state_name", "source_state_normalized")
    .agg(
        F.count("*").alias("total_facilities"),
        F.sum(F.col("has_valid_coordinates").cast("int")).alias("valid_coordinate_facilities"),
        F.sum(F.col("has_pincode").cast("int")).alias("pincode_present_facilities"),
        F.sum(F.col("has_capability_text").cast("int")).alias("capability_text_facilities"),
        F.avg(F.col("care_substance_missing_count").cast("double")).alias("avg_care_substance_missing_count"),
    )
    .withColumn(
        "location_trust_score",
        F.when(F.col("total_facilities") > 0, F.col("valid_coordinate_facilities") / F.col("total_facilities")),
    )
    .withColumn(
        "data_completeness_score",
        F.when(
            F.col("total_facilities") > 0,
            (
                F.col("pincode_present_facilities") / F.col("total_facilities")
                + F.col("capability_text_facilities") / F.col("total_facilities")
                + (4.0 - F.col("avg_care_substance_missing_count")) / 4.0
            )
            / 3.0,
        ),
    )
    .withColumn(
        "numeric_score",
        (
            F.coalesce(F.col("location_trust_score"), F.lit(0.0))
            + F.coalesce(F.col("data_completeness_score"), F.lit(0.0))
        )
        / 2.0,
    )
    .withColumn(
        "band",
        F.when(F.col("numeric_score") >= 0.85, F.lit("green"))
        .when(F.col("numeric_score") >= 0.60, F.lit("amber"))
        .otherwise(F.lit("red")),
    )
    .withColumn(
        "binding_reason",
        F.when(
            F.coalesce(F.col("location_trust_score"), F.lit(0.0))
            <= F.coalesce(F.col("data_completeness_score"), F.lit(0.0)),
            F.lit("Location: invalid or out-of-country coordinates constrain trust"),
        ).otherwise(F.lit("Completeness: sparse care-substance fields constrain trust")),
    )
    .withColumn("geo_grain", F.lit("state"))
    .withColumn("data_caution", F.lit("state_rollup_before_district_polygon_assignment"))
)

write_delta(district_health_context, catalog, schema, "gold_district_health_context")
write_delta(pincode_enrichment, catalog, schema, "gold_pincode_health_enrichment")
write_delta(underserved_candidates, catalog, schema, "gold_underserved_district_candidates")
write_delta(hmis_state_indicator_summary, catalog, schema, "gold_hmis_state_indicator_summary")
write_delta(facility_verdicts, catalog, schema, "gold_facility_verdicts")

display(underserved_candidates.orderBy(F.desc("demand_side_need_score")).limit(25))
