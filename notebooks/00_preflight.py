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

source_volume_path = dbutils.widgets.get("source_volume_path").rstrip("/")
required_files = [
    dbutils.widgets.get("pincode_file"),
    dbutils.widgets.get("nfhs_file"),
    dbutils.widgets.get("hmis_file"),
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

display(
    spark.createDataFrame(
        [(source_volume_path, file_name, "present") for file_name in required_files],
        ["source_volume_path", "file_name", "status"],
    )
)
