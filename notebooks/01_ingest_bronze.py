# Databricks notebook source
"""Ingest source CSV files from a Unity Catalog Volume into bronze Delta tables."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, DoubleType, StringType, StructField, StructType

if TYPE_CHECKING:
    dbutils: Any
    display: Callable[[object], None]
    spark: SparkSession

PINCODE_SCHEMA = StructType(
    [
        StructField("circlename", StringType(), True),
        StructField("regionname", StringType(), True),
        StructField("divisionname", StringType(), True),
        StructField("officename", StringType(), True),
        StructField("pincode", StringType(), True),
        StructField("officetype", StringType(), True),
        StructField("delivery", StringType(), True),
        StructField("district", StringType(), True),
        StructField("statename", StringType(), True),
        StructField("latitude", StringType(), True),
        StructField("longitude", StringType(), True),
    ]
)
NFHS_SCHEMA = StructType(
    [
        StructField("state", StringType(), True),
        StructField("district", StringType(), True),
        StructField("placeholder_indicator", StringType(), True),
    ]
)
SRS_SCHEMA = StructType(
    [
        StructField("state", StringType(), True),
        StructField("birth_rate_total", DoubleType(), True),
        StructField("death_rate_total", DoubleType(), True),
        StructField("natural_growth_rate_total", DoubleType(), True),
        StructField("infant_mortality_rate_total", StringType(), True),
    ]
)
DISTRICT_BOUNDARIES_SCHEMA = StructType(
    [
        StructField("state", StringType(), True),
        StructField("district", StringType(), True),
        StructField("geometry_available", BooleanType(), True),
    ]
)


def table_name(catalog_name: str, schema_name: str, table: str) -> str:
    """Return a quoted Unity Catalog table name."""
    return f"`{catalog_name}`.`{schema_name}`.`{table}`"


def read_csv(spark_session: SparkSession, path: str, encoding: str = "UTF-8") -> DataFrame:
    """Read a CSV source as strings."""
    return (
        spark_session.read.option("header", True)
        .option("inferSchema", False)
        .option("encoding", encoding)
        .option("multiLine", True)
        .option("escape", '"')
        .csv(path)
    )


def with_ingest_metadata(df: DataFrame, source_file: str, layer: str) -> DataFrame:
    """Add ingest metadata to a dataframe."""
    return (
        df.withColumn("_source_file", F.lit(source_file))
        .withColumn("_medallion_layer", F.lit(layer))
        .withColumn("_ingested_at_utc", F.current_timestamp())
    )


def write_delta(df: DataFrame, catalog_name: str, schema_name: str, table: str) -> None:
    """Overwrite a managed Delta table."""
    (
        df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .option("delta.columnMapping.mode", "name")
        .option("delta.minReaderVersion", "2")
        .option("delta.minWriterVersion", "5")
        .format("delta")
        .saveAsTable(table_name(catalog_name, schema_name, table))
    )


dbutils.widgets.text("catalog", "data_readiness_desk")
dbutils.widgets.text("schema", "pipeline")
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

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
source_volume_path = dbutils.widgets.get("source_volume_path").rstrip("/")
pincode_file = dbutils.widgets.get("pincode_file")
nfhs_file = dbutils.widgets.get("nfhs_file")
hmis_file = dbutils.widgets.get("hmis_file")
srs_file = dbutils.widgets.get("srs_file")
district_boundaries_file = dbutils.widgets.get("district_boundaries_file")
facilities_table = dbutils.widgets.get("facilities_table")


spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")

pincode_path = f"{source_volume_path}/{pincode_file}"
nfhs_path = f"{source_volume_path}/{nfhs_file}"
hmis_path = f"{source_volume_path}/{hmis_file}"
srs_path = f"{source_volume_path}/{srs_file}"
district_boundaries_path = f"{source_volume_path}/{district_boundaries_file}"

available_files = {item.name.rstrip("/") for item in dbutils.fs.ls(source_volume_path)}
pincode_df = (
    read_csv(spark, pincode_path) if pincode_file in available_files else spark.createDataFrame([], PINCODE_SCHEMA)
)
nfhs_df = read_csv(spark, nfhs_path) if nfhs_file in available_files else spark.createDataFrame([], NFHS_SCHEMA)
hmis_df = read_csv(spark, hmis_path, encoding="windows-1252")
srs_df = read_csv(spark, srs_path) if srs_file in available_files else spark.createDataFrame([], SRS_SCHEMA)
district_boundaries_df = (
    spark.read.option("multiLine", True).json(district_boundaries_path)
    if district_boundaries_file in available_files
    else spark.createDataFrame([], DISTRICT_BOUNDARIES_SCHEMA)
)
facilities_df = spark.table(facilities_table)

write_delta(
    with_ingest_metadata(facilities_df, facilities_table, "bronze"),
    catalog,
    schema,
    "bronze_facilities",
)

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
write_delta(
    with_ingest_metadata(srs_df, srs_path, "bronze"),
    catalog,
    schema,
    "bronze_srs_2020_state",
)
write_delta(
    with_ingest_metadata(district_boundaries_df, district_boundaries_path, "bronze"),
    catalog,
    schema,
    "bronze_india_district_boundaries",
)

summary_rows = [
    ("bronze_facilities", facilities_df.count(), facilities_table),
    ("bronze_india_post_pincode_directory", pincode_df.count(), pincode_path),
    ("bronze_nfhs5_district_health_indicators", nfhs_df.count(), nfhs_path),
    ("bronze_hmis_2019_20_slice", hmis_df.count(), hmis_path),
    ("bronze_srs_2020_state", srs_df.count(), srs_path),
    ("bronze_india_district_boundaries", district_boundaries_df.count(), district_boundaries_path),
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
