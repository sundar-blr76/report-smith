"""
JSON viewer component using native Streamlit components.
Simple and reliable - no custom state management, just uses st.json and st.code.
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
    Render JSON data inside an expander.

    Uses native st.json which provides built-in expand/collapse for nested items.
    Users can click the ▼ arrows next to each item to expand/collapse.

    Args:
        data: The data to display as JSON
        title: Title for the expander
        key: Unique key for this viewer instance (unused, kept for compatibility)
        expanded: Whether the expander should be initially expanded
        height: Height of the JSON viewer (unused, kept for compatibility)
    """
    with st.expander(title, expanded=expanded):
        # Simple info about how to use the viewer
        st.caption(
            "💡 Click ▼ arrows to expand/collapse individual items | Use Copy button to copy JSON"
        )

        # Use native st.json - it has built-in expand/collapse
        # The expanded parameter controls initial state of nested items
        st.json(data, expanded=True)


def render_json_viewer(
    data: Any,
    key: str,
    height: int = 300,
) -> None:
    """
    Render JSON data without expander.

    Args:
        data: The data to display as JSON
        key: Unique key for this viewer instance (unused, kept for compatibility)
        height: Height of the viewer (unused, kept for compatibility)
    """
    st.caption("💡 Click ▼ arrows to expand/collapse individual items")
    st.json(data, expanded=True)
