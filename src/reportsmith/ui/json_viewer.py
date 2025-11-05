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
    Render JSON data inside an expander with expand/collapse all controls.

    Args:
        data: The data to display as JSON
        title: Title for the expander
        key: Unique key for this viewer instance
        expanded: Whether the expander should be initially expanded
        height: Height of the JSON viewer
    """
    with st.expander(title, expanded=expanded):
        # Initialize session state for this viewer if not present
        expand_state_key = f"{key}_expanded_state"
        if expand_state_key not in st.session_state:
            st.session_state[expand_state_key] = 1  # 1 = expanded, 0 = collapsed
        
        # Controls for expand/collapse all
        col1, col2, col3 = st.columns([1, 1, 6])
        
        with col1:
            if st.button("▼ Expand All", key=f"btn_expand_{key}", use_container_width=True):
                st.session_state[expand_state_key] = 1
        
        with col2:
            if st.button("▶ Collapse All", key=f"btn_collapse_{key}", use_container_width=True):
                st.session_state[expand_state_key] = 0
        
        # Render JSON with appropriate expansion state
        # Use the session state value directly as the expanded parameter
        st.json(data, expanded=st.session_state[expand_state_key])


def render_json_viewer(
    data: Any,
    key: str,
    height: int = 300,
) -> None:
    """
    Render JSON data without expander but with expand/collapse controls.

    Args:
        data: The data to display as JSON
        key: Unique key for this viewer instance
        height: Height of the viewer
    """
    # Initialize session state for this viewer if not present
    expand_state_key = f"{key}_expanded_state"
    if expand_state_key not in st.session_state:
        st.session_state[expand_state_key] = 1  # 1 = expanded, 0 = collapsed
    
    # Controls for expand/collapse all
    col1, col2, col3 = st.columns([1, 1, 6])
    
    with col1:
        if st.button("▼ Expand All", key=f"btn_expand_{key}", use_container_width=True):
            st.session_state[expand_state_key] = 1
    
    with col2:
        if st.button("▶ Collapse All", key=f"btn_collapse_{key}", use_container_width=True):
            st.session_state[expand_state_key] = 0
    
    # Render JSON with appropriate expansion state
    st.json(data, expanded=st.session_state[expand_state_key])
