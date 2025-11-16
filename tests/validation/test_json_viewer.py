#!/usr/bin/env python3
"""
Quick test script for JSON viewer expand/collapse functionality.
Run with: streamlit run test_json_viewer.py
"""

import streamlit as st
from src.reportsmith.ui.json_viewer import render_json_in_expander

st.title("JSON Viewer Test")

# Sample complex JSON data
test_data = {
    "query": "Show monthly fees for equity funds",
    "intent": {
        "type": "aggregation",
        "time_scope": "monthly",
        "filters": ["equity"],
    },
    "entities": [
        {
            "text": "fees",
            "type": "metric",
            "table": "fee_transactions",
            "column": "fee_amount",
        },
        {
            "text": "equity",
            "type": "dimension_value",
            "table": "funds",
            "column": "fund_type",
        },
    ],
    "sql": {
        "query": "SELECT DATE_TRUNC('month', payment_date) as month, SUM(fee_amount) FROM fee_transactions...",
        "explanation": "This query aggregates fees by month",
    },
    "execution": {
        "rows": [
            {"month": "2024-01", "total": 15000},
            {"month": "2024-02", "total": 16500},
            {"month": "2024-03", "total": 14200},
        ],
        "row_count": 3,
    },
}

st.write("Test the expand/collapse all buttons below:")

render_json_in_expander(
    test_data,
    title="Test JSON Data",
    key="test_viewer",
    expanded=True,
)

st.write("---")
st.success("If you see Expand All and Collapse All buttons, the feature is working!")
