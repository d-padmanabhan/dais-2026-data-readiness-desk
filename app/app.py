#!/usr/bin/env -S uv run

"""
Render the Data Readiness Desk Streamlit application.

This script provides the Databricks App entrypoint for the hackathon demo. It
renders a lens selector, accepts a user query, and displays the UI shape for
cached Trust Verdict outputs. The app is deliberately read-only: production
logic must precompute verdicts, fixes, and before/after states into gold tables
before the demo.

Workflow:
1. Configure the Streamlit page.
2. Collect the selected lens and user query.
3. Render a placeholder Trust Verdict card until cached gold tables are ready.
4. Show the expected gold tables that future app wiring should read.

Usage:
    streamlit run app.py

Environment:
    DATABRICKS_HOST: Databricks workspace host.
    DATABRICKS_WAREHOUSE_ID: SQL Warehouse ID used by the app.
    DATABRICKS_TOKEN: Token made available to the app runtime.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import streamlit as st
from databricks import sql


def query_cached_gold(sql_text: str) -> Sequence[object]:
    """
    Run a read-only query against cached gold tables.

    Args:
        sql_text: SELECT statement against gold tables.

    Returns:
        Query result rows.

    Raises:
        KeyError: If required Databricks environment variables are missing.
        databricks.sql.exc.Error: If the SQL Warehouse query fails.
    """
    with sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"],
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        access_token=os.environ["DATABRICKS_TOKEN"],
    ) as connection:
        return connection.cursor().execute(sql_text).fetchall()


def render_placeholder_verdict(lens: str, query: str) -> None:
    """
    Render the intended UI shape before gold verdict tables are populated.

    Args:
        lens: Selected user lens.
        query: User search input.

    Returns:
        None.
    """
    st.subheader("Trust Verdict")
    st.warning("Gold verdict tables are not populated yet. This screen is wired for cached reads only.")
    st.metric("Lens", lens)
    st.metric("Query", query or "None")
    st.caption("Expected: band, numeric score, binding dimension, ranked fixes, and before/after delta.")


def main() -> None:
    """
    Render the Data Readiness Desk app.

    Returns:
        None.
    """
    st.set_page_config(page_title="Data Readiness Desk", layout="wide")
    st.title("Data Readiness Desk")
    st.caption("Can I trust the data for a place, condition, or facility?")

    lens = st.radio("Lens", ["Location", "Disease / Condition", "Facility"], horizontal=True)
    query = st.text_input("Place, condition, or facility")

    if not query:
        st.info("Enter a query to inspect cached readiness outputs.")
        return

    render_placeholder_verdict(lens, query)

    st.subheader("Cached Gold Tables")
    st.code(
        "\n".join(
            [
                "drd.gold.facility_verdicts",
                "drd.gold.district_verdicts",
                "drd.gold.fix_ranking",
                "drd.gold.coverage_predictions",
            ]
        ),
        language="text",
    )


if __name__ == "__main__":
    main()
