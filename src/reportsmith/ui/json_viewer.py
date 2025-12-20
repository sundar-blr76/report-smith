"""
JSON viewer component using native Streamlit components with expand/collapse controls.
"""

import json
from typing import Any

import streamlit as st


def render_json_in_expander(
    data: Any,
    title: str,
    key: str,
    expanded: bool = False,
    height: int = 300,
) -> None:
    """
    Render JSON data inside an expander using standard st.json.

    Args:
        data: The data to display as JSON
        title: Title for the expander
        key: Unique key for this viewer instance
        expanded: Whether the expander should be initially expanded
        height: Height to display (ignored for native st.json)
    """
    with st.expander(title, expanded=expanded):
        st.json(data, expanded=False)


def render_json_viewer(
    data: Any,
    key: str,
    height: int = 300,
) -> None:
    """
    Render JSON data using standard st.json.

    Args:
        data: The data to display as JSON
        key: Unique key for this viewer instance
    """
    st.json(data, expanded=False)
