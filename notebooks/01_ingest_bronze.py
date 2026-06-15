# Databricks notebook source
"""Ingest source CSV files from a Unity Catalog Volume into bronze Delta tables."""

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

from data_readiness_desk.spark_helpers import read_csv, table_name, with_ingest_metadata, write_delta  # noqa: E402

dbutils.widgets.text("catalog", "data_readiness_desk")
dbutils.widgets.text("schema", "pipeline")
dbutils.widgets.text("source_volume_path", "/Volumes/data_readiness_desk/bronze/files")
dbutils.widgets.text("pincode_file", "india_post_pincode_directory.csv")
dbutils.widgets.text("nfhs_file", "nfhs5_district_health_indicators.csv")
dbutils.widgets.text("hmis_file", "hmis_2019_20_slice.csv")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
source_volume_path = dbutils.widgets.get("source_volume_path").rstrip("/")
pincode_file = dbutils.widgets.get("pincode_file")
nfhs_file = dbutils.widgets.get("nfhs_file")
hmis_file = dbutils.widgets.get("hmis_file")


spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")

pincode_path = f"{source_volume_path}/{pincode_file}"
nfhs_path = f"{source_volume_path}/{nfhs_file}"
hmis_path = f"{source_volume_path}/{hmis_file}"

pincode_df = read_csv(spark, pincode_path)
nfhs_df = read_csv(spark, nfhs_path)
hmis_df = read_csv(spark, hmis_path, encoding="windows-1252")

write_delta(
    with_ingest_metadata(pincode_df, pincode_path, "bronze"),
    catalog,
    schema,
    "bronze_india_post_pincode_directory",
)
write_delta(
    with_ingest_metadata(nfhs_df, nfhs_path, "bronze"),
    catalog,
    schema,
    "bronze_nfhs5_district_health_indicators",
)
write_delta(
    with_ingest_metadata(hmis_df, hmis_path, "bronze"),
    catalog,
    schema,
    "bronze_hmis_2019_20_slice",
)

summary_rows = [
    ("bronze_india_post_pincode_directory", pincode_df.count(), pincode_path),
    ("bronze_nfhs5_district_health_indicators", nfhs_df.count(), nfhs_path),
    ("bronze_hmis_2019_20_slice", hmis_df.count(), hmis_path),
]

summary_df = spark.createDataFrame(summary_rows, ["table_name", "row_count", "source_path"])
(
    summary_df.withColumn("_recorded_at_utc", F.current_timestamp())
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .format("delta")
    .saveAsTable(table_name(catalog, schema, "pipeline_run_summary"))
)

display(summary_df)
