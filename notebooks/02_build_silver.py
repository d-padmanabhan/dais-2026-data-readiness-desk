# Databricks notebook source
"""Build silver tables with normalized geography and explicit quality flags."""

import sys
from collections.abc import Callable
from functools import reduce
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

sys.path.append(str(Path.cwd() / "src"))

from data_readiness_desk.hmis import parse_hmis_measure_column  # noqa: E402
from data_readiness_desk.spark_helpers import (  # noqa: E402
    first_existing,
    normalize_column_text,
    rename_columns,
    require_columns,
    table_name,
    write_delta,
)

dbutils.widgets.text("catalog", "hackathon")
dbutils.widgets.text("schema", "virtue_foundation")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")


def parsed_indicator_long(df: DataFrame, state_col: str, district_col: str) -> DataFrame:
    """Convert wide NFHS indicator columns into a quality-aware long table.

    Args:
        df: Normalized NFHS dataframe.
        state_col: State column name.
        district_col: District column name.

    Returns:
        Long-form dataframe with parsed numeric values and quality flags.

    Raises:
        ValueError: If no indicator columns are available after geography columns.
    """
    id_cols = {
        state_col,
        district_col,
        "state_normalized",
        "district_normalized",
        "_source_file",
        "_ingested_at_utc",
    }
    indicator_cols = [col for col in df.columns if col not in id_cols]
    if not indicator_cols:
        raise ValueError("NFHS dataset has no indicator columns after geography fields were excluded")

    frames = [
        df.select(
            F.col(state_col).alias("state_name"),
            F.col(district_col).alias("district_name"),
            "state_normalized",
            "district_normalized",
            F.lit(col).alias("indicator_name"),
            F.col(col).cast("string").alias("raw_value"),
        )
        for col in indicator_cols
    ]
    long_df = reduce(DataFrame.unionByName, frames)
    cleaned_raw = F.trim(F.col("raw_value"))
    number_text = F.regexp_extract(F.regexp_replace(cleaned_raw, ",", ""), r"[-+]?\d+(?:\.\d+)?", 0)
    return (
        long_df.withColumn("is_suppressed", cleaned_raw == F.lit("*"))
        .withColumn("is_low_sample_estimate", cleaned_raw.rlike(r"^\([-+]?\d+(?:\.\d+)?\)$"))
        .withColumn(
            "value",
            F.when(F.col("is_suppressed"), F.lit(None).cast("double"))
            .when(number_text == "", F.lit(None).cast("double"))
            .otherwise(number_text.cast("double")),
        )
    )


def parsed_hmis_long(df: DataFrame) -> DataFrame:
    """Convert HMIS wide monthly columns into a long state-grain table.

    Args:
        df: Raw HMIS bronze dataframe.

    Returns:
        Long-form HMIS dataframe with parsed numeric values and invalid-value flags.

    Raises:
        ValueError: If required metadata columns or measure columns are missing.
    """
    require_columns(df, {"State", "S.No.", "Parameters", "Type"}, "HMIS 2019-20 slice")
    measure_columns = [
        measure_column
        for column_name in df.columns
        if (measure_column := parse_hmis_measure_column(column_name)) is not None
    ]
    if not measure_columns:
        raise ValueError("HMIS 2019-20 slice has no parseable month/value measure columns")

    value_structs = [
        F.struct(
            F.lit(measure_column.source_column).alias("source_column"),
            F.lit(measure_column.month).alias("month"),
            F.lit(measure_column.value_type).alias("value_type"),
            F.col(measure_column.source_column).cast("string").alias("raw_value"),
        )
        for measure_column in measure_columns
    ]
    exploded = df.withColumn("measure", F.explode(F.array(*value_structs)))
    cleaned_raw = F.trim(F.regexp_replace(F.col("measure.raw_value"), "\u00a0", " "))
    numeric_text = F.regexp_replace(cleaned_raw, ",", "")
    is_unavailable = F.upper(cleaned_raw).isin("", "NA", "N/A", "NULL", "-")
    is_integer = numeric_text.rlike(r"^-?\d+$")
    return exploded.select(
        F.col("State").alias("state_name"),
        normalize_column_text("State").alias("state_normalized"),
        F.regexp_replace(F.trim(F.col("S.No.").cast("string")), "'", "").alias("serial_number"),
        F.regexp_replace(F.trim(F.col("Parameters").cast("string")), "\u00a0", " ").alias("parameter"),
        F.trim(F.col("Type").cast("string")).alias("reporting_type"),
        F.col("measure.source_column").alias("source_column"),
        F.col("measure.month").alias("month"),
        F.col("measure.value_type").alias("value_type"),
        F.col("measure.raw_value").alias("raw_value"),
        F.when(is_unavailable, F.lit(None).cast("long"))
        .when(is_integer, numeric_text.cast("long"))
        .otherwise(F.lit(None).cast("long"))
        .alias("value"),
        (~is_unavailable & ~is_integer).alias("is_invalid_numeric"),
        F.lit("state").alias("geo_grain"),
        F.lit("2019-20").alias("source_period"),
    ).withColumn("_recorded_at_utc", F.current_timestamp())


pincode_bronze = spark.table(table_name(catalog, schema, "bronze_india_post_pincode_directory"))
nfhs_bronze = spark.table(table_name(catalog, schema, "bronze_nfhs5_district_health_indicators"))
hmis_bronze = spark.table(table_name(catalog, schema, "bronze_hmis_2019_20_slice"))

pincode = rename_columns(pincode_bronze)
require_columns(
    pincode,
    {"district", "latitude", "longitude", "pincode", "statename"},
    "India Post PIN code directory",
)
pincode = (
    pincode.withColumn("pincode", F.lpad(F.regexp_extract(F.col("pincode").cast("string"), r"\d+", 0), 6, "0"))
    .withColumn("district_normalized", normalize_column_text("district"))
    .withColumn("state_normalized", normalize_column_text("statename"))
    .withColumn(
        "latitude", F.when(F.upper(F.trim(F.col("latitude"))) == "NA", None).otherwise(F.col("latitude")).cast("double")
    )
    .withColumn(
        "longitude",
        F.when(F.upper(F.trim(F.col("longitude"))) == "NA", None).otherwise(F.col("longitude")).cast("double"),
    )
    .withColumn("has_coordinates", F.col("latitude").isNotNull() & F.col("longitude").isNotNull())
)

pin_lookup = (
    pincode.groupBy("pincode")
    .agg(
        F.count("*").alias("post_office_count"),
        F.countDistinct("district_normalized").alias("district_count"),
        F.countDistinct("state_normalized").alias("state_count"),
        F.array_sort(F.collect_set("district_normalized")).alias("districts_normalized"),
        F.array_sort(F.collect_set("state_normalized")).alias("states_normalized"),
        F.array_sort(F.collect_set("district")).alias("district_names"),
        F.array_sort(F.collect_set("statename")).alias("state_names"),
        F.sum(F.when(F.col("has_coordinates"), 1).otherwise(0)).alias("geocoded_office_count"),
    )
    .withColumn("is_geography_ambiguous", (F.col("district_count") > 1) | (F.col("state_count") > 1))
    .withColumn(
        "representative_district_normalized",
        F.when(~F.col("is_geography_ambiguous"), F.element_at("districts_normalized", 1)),
    )
    .withColumn(
        "representative_state_normalized",
        F.when(~F.col("is_geography_ambiguous"), F.element_at("states_normalized", 1)),
    )
)

nfhs = rename_columns(nfhs_bronze)
state_col = first_existing(nfhs.columns, ["state", "state_ut", "state_name", "states_ut"])
district_col = first_existing(nfhs.columns, ["district", "district_name", "districts"])

if state_col is None or district_col is None:
    raise ValueError(f"Could not identify NFHS geography columns. Available columns: {nfhs.columns}")

nfhs = nfhs.withColumn("state_normalized", normalize_column_text(state_col)).withColumn(
    "district_normalized", normalize_column_text(district_col)
)
nfhs_quality_long = parsed_indicator_long(nfhs, state_col, district_col)

nfhs_wide = (
    nfhs_quality_long.groupBy("state_name", "district_name", "state_normalized", "district_normalized")
    .pivot("indicator_name")
    .agg(F.first("value", ignorenulls=True))
)

nfhs_quality_summary = nfhs_quality_long.groupBy("state_normalized", "district_normalized").agg(
    F.count("*").alias("indicator_cell_count"),
    F.sum(F.col("is_suppressed").cast("int")).alias("suppressed_indicator_count"),
    F.sum(F.col("is_low_sample_estimate").cast("int")).alias("low_sample_estimate_count"),
)

nfhs_silver = nfhs_wide.join(
    nfhs_quality_summary,
    on=["state_normalized", "district_normalized"],
    how="left",
)
hmis_long = parsed_hmis_long(hmis_bronze)

quality_checks = spark.createDataFrame(
    [
        ("pincode_required_columns_present", "pass", len(pincode.columns)),
        ("pincode_lookup_is_unique", "pass", pin_lookup.select("pincode").distinct().count()),
        ("nfhs_geography_columns_detected", "pass", 2),
        ("nfhs_indicator_columns_detected", "pass", nfhs_quality_long.select("indicator_name").distinct().count()),
        ("hmis_state_grain_detected", "pass", hmis_long.select("state_normalized").distinct().count()),
        ("hmis_invalid_numeric_count", "warn", hmis_long.filter(F.col("is_invalid_numeric")).count()),
    ],
    ["check_name", "status", "observed_value"],
).withColumn("_recorded_at_utc", F.current_timestamp())

write_delta(pincode, catalog, schema, "silver_pincode_post_offices")
write_delta(pin_lookup, catalog, schema, "silver_pincode_lookup")
write_delta(nfhs_quality_long, catalog, schema, "silver_nfhs_indicator_quality_long")
write_delta(nfhs_silver, catalog, schema, "silver_nfhs5_district_health_indicators")
write_delta(hmis_long, catalog, schema, "silver_hmis_2019_20_long")
write_delta(quality_checks, catalog, schema, "pipeline_quality_checks")

display(
    spark.createDataFrame(
        [
            ("silver_pincode_post_offices", pincode.count()),
            ("silver_pincode_lookup", pin_lookup.count()),
            ("silver_nfhs_indicator_quality_long", nfhs_quality_long.count()),
            ("silver_nfhs5_district_health_indicators", nfhs_silver.count()),
            ("silver_hmis_2019_20_long", hmis_long.count()),
        ],
        ["table_name", "row_count"],
    )
)
