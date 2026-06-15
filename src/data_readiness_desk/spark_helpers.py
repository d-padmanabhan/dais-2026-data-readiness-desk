"""
Provide small PySpark helpers used by Databricks notebooks.

These helpers keep notebook code thin and reproducible. They centralize table
naming, CSV read options, metadata stamping, and contract checks that are shared
across bronze, silver, and gold notebooks.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

from data_readiness_desk.normalization import to_snake_case


def table_name(catalog: str, schema: str, table: str) -> str:
    """
    Return a Unity Catalog three-part table name.

    Args:
        catalog: Unity Catalog catalog name.
        schema: Unity Catalog schema name.
        table: Table name.

    Returns:
        Quoted three-part table identifier.
    """
    return f"`{catalog}`.`{schema}`.`{table}`"


def read_csv(spark: SparkSession, path: str, encoding: str = "UTF-8") -> DataFrame:
    """
    Read a source CSV with options suitable for public-sector extracts.

    Args:
        spark: Active Spark session.
        path: CSV path in a Unity Catalog Volume.
        encoding: Java charset name used to decode the source file.

    Returns:
        Source dataframe with all columns read as strings.
    """
    return (
        spark.read.option("header", True)
        .option("inferSchema", False)
        .option("encoding", encoding)
        .option("multiLine", True)
        .option("escape", '"')
        .csv(path)
    )


def with_ingest_metadata(df: DataFrame, source_file: str, layer: str) -> DataFrame:
    """
    Add reproducibility metadata to a dataframe before publishing.

    Args:
        df: Source dataframe.
        source_file: Source file path.
        layer: Medallion layer name.

    Returns:
        Dataframe with ingestion metadata columns.
    """
    return (
        df.withColumn("_source_file", F.lit(source_file))
        .withColumn("_medallion_layer", F.lit(layer))
        .withColumn("_ingested_at_utc", F.current_timestamp())
    )


def write_delta(df: DataFrame, catalog: str, schema: str, table: str) -> None:
    """
    Overwrite a managed Delta table with schema evolution.

    Args:
        df: Dataframe to publish.
        catalog: Unity Catalog catalog name.
        schema: Unity Catalog schema name.
        table: Target table name.
    """
    (
        df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .format("delta")
        .saveAsTable(table_name(catalog, schema, table))
    )


def normalize_column_text(column: str) -> Column:
    """
    Normalize a text column for approximate state and district matching.

    Args:
        column: Input column name.

    Returns:
        Spark column expression with lowercase, punctuation-stripped text.
    """
    return F.when(
        F.col(column).isNotNull(),
        F.regexp_replace(F.regexp_replace(F.lower(F.trim(F.col(column))), r"[^0-9a-z ]+", ""), r"\s+", " "),
    )


def rename_columns(df: DataFrame) -> DataFrame:
    """
    Rename dataframe columns to unique snake_case names.

    Args:
        df: Input dataframe.

    Returns:
        Dataframe with deterministic snake_case column names.
    """
    renamed = df
    seen: dict[str, int] = {}
    for original in df.columns:
        proposed = to_snake_case(original)
        count = seen.get(proposed, 0)
        seen[proposed] = count + 1
        new_name = proposed if count == 0 else f"{proposed}_{count + 1}"
        renamed = renamed.withColumnRenamed(original, new_name)
    return renamed


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    """
    Return the first candidate column that exists.

    Args:
        columns: Available dataframe columns.
        candidates: Candidate names in priority order.

    Returns:
        The first existing column name, or None when no candidate exists.
    """
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def require_columns(df: DataFrame, required_columns: set[str], dataset_name: str) -> None:
    """
    Fail fast when a required dataset contract column is missing.

    Args:
        df: Dataframe to validate.
        required_columns: Required column names.
        dataset_name: Human-readable dataset name for error messages.

    Raises:
        ValueError: If any required columns are missing.
    """
    missing = sorted(required_columns.difference(df.columns))
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")


def current_run_id(prefix: str) -> str:
    """
    Build a simple run id for notebook logs and quality tables.

    Args:
        prefix: Run identifier prefix.

    Returns:
        Stable run identifier containing a UTC timestamp.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"
