# Databricks notebook source
"""Validate source Volume inputs before running the pipeline."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyspark.sql import SparkSession

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

dbutils.widgets.text("source_volume_path", "/Volumes/data_readiness_desk/bronze/files")
dbutils.widgets.text("pincode_file", "india_post_pincode_directory.csv")
dbutils.widgets.text("nfhs_file", "nfhs5_district_health_indicators.csv")
dbutils.widgets.text("hmis_file", "hmis_2019_20_slice.csv")
dbutils.widgets.text("srs_file", "srs_2020_state.csv")
dbutils.widgets.text("district_boundaries_file", "india_districts.geojson")
dbutils.widgets.text(
    "facilities_table",
    "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities",
)

source_volume_path = dbutils.widgets.get("source_volume_path").rstrip("/")
facilities_table = dbutils.widgets.get("facilities_table")
required_files = [
    dbutils.widgets.get("hmis_file"),
]
optional_files = [
    dbutils.widgets.get("pincode_file"),
    dbutils.widgets.get("nfhs_file"),
    dbutils.widgets.get("srs_file"),
    dbutils.widgets.get("district_boundaries_file"),
]

try:
    available_files = {item.name.rstrip("/") for item in dbutils.fs.ls(source_volume_path)}
except Exception as error:
    raise ValueError(f"Source volume path is not readable: {source_volume_path}") from error

missing_files = sorted(file_name for file_name in required_files if file_name not in available_files)
if missing_files:
    raise ValueError(
        "Missing required source files in "
        f"{source_volume_path}: {missing_files}. "
        f"Available files: {sorted(available_files)}"
    )

missing_optional_files = sorted(file_name for file_name in optional_files if file_name not in available_files)

try:
    facilities_count = spark.table(facilities_table).count()
except Exception as error:
    raise ValueError(f"Facilities source table is not readable: {facilities_table}") from error

display(
    spark.createDataFrame(
        [(source_volume_path, file_name, "file_present", None) for file_name in required_files]
        + [(source_volume_path, file_name, "optional_file_missing", None) for file_name in missing_optional_files]
        + [(facilities_table, "facilities", "table_readable", facilities_count)],
        ["source_location", "source_name", "status", "row_count"],
    )
)
