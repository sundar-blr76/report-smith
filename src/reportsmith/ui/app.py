import json
import time
from typing import Any, Dict, Optional

import requests
import streamlit as st

st.set_page_config(page_title="ReportSmith UI", page_icon="📊", layout="wide")

# Sidebar configuration
st.sidebar.title("Settings")
api_base: str = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
timeout_s: int = st.sidebar.number_input("Timeout (seconds)", min_value=1, max_value=120, value=30)

# Optional: manual refresh
st.sidebar.button("Refresh status")

# Small helper to check an endpoint with a couple retries (warm-up)
def _check_endpoint(path: str, tries: int = 3, timeout: int = 10):
    last_err = None
    for i in range(tries):
        try:
            resp = requests.get(f"{api_base}{path}", timeout=timeout)
            return resp
        except requests.exceptions.RequestException as e:
            last_err = e
            time.sleep(1)
    raise last_err if last_err else RuntimeError("Unknown error")

# Health check
health_status = "unknown"
try:
    r = _check_endpoint("/health")
    if r.ok and r.json().get("status") == "ok":
        health_status = "healthy"
    else:
        health_status = f"unavailable ({r.status_code})"
except Exception as e:
    health_status = f"error: {e.__class__.__name__}"

# Readiness check
ready_status = "unknown"
ready_ok = False
try:
    rr = _check_endpoint("/ready")
    if rr.status_code == 200:
        ready_ok = True
        ready_status = "ready"
    else:
        ready_status = f"not ready ({rr.status_code})"
except Exception as e:
    ready_status = f"error: {e.__class__.__name__}"

st.sidebar.markdown(f"**API Health:** {health_status}")
st.sidebar.markdown(f"**API Ready:** {ready_status}")

st.title("ReportSmith – Interactive Query")
st.caption("Enter a natural language question, send to the API, and view structured JSON output.")


# Sample queries with varying complexity
samples = [
    "Show monthly fees for all equity funds",
    "What is the total AUM for bond funds by fund type?",
    "List top 10 clients by account balance for the last quarter",
    "Compare average fees between equity and bond funds in 2024",
    "Show daily transactions for account 12345 between 2025-01-01 and 2025-01-31",
]

with st.expander("Sample queries", expanded=True):
    for i, q in enumerate(samples, start=1):
        if st.button(f"Use sample {i}", key=f"sample_{i}"):
            st.session_state["rs_sample_query"] = q
    st.code("\n".join(f"- {q}" for q in samples))

with st.form("query_form"):
    default_q = st.session_state.get("rs_sample_query") or ""
    question = st.text_area("Question", value=default_q, placeholder="Show monthly fees for all equity funds", height=100)
    app_id = st.text_input("App ID (optional)", value="")
    submitted = st.form_submit_button("Send Query")

if submitted:
    if not question.strip():
        st.warning("Please enter a question.")
    elif not ready_ok:
        st.warning("API is not ready yet. Please wait a few seconds and try again.")
    else:
        payload: Dict[str, Any] = {"question": question}
        if app_id.strip():
            payload["app_id"] = app_id.strip()

        with st.spinner("Sending request to API..."):
            start = time.time()
            try:
                resp = requests.post(f"{api_base}/query", json=payload, timeout=timeout_s)
                elapsed = time.time() - start
                st.caption(f"Completed in {elapsed:.2f}s (status {resp.status_code})")

                trace_id = resp.headers.get("X-Request-ID")
                if trace_id:
                    st.caption(f"Trace ID: {trace_id}")

                if not resp.ok:
                    # Try to extract detail, including readiness error payload
                    try:
                        body = resp.json()
                        detail = body.get("detail", body)
                    except Exception:
                        detail = resp.text
                    st.error(f"Request failed: {detail}")
                else:
                    data = resp.json()
                    st.subheader("Response")
                    st.json(data)

                    # Convenience views if present
                    result = data.get("data", {}) if isinstance(data, dict) else {}
                    if result:
                        with st.expander("Intent", expanded=False):
                            st.json(result.get("intent", {}))
                        with st.expander("Entities", expanded=False):
                            st.json(result.get("entities", []))
                        with st.expander("Tables", expanded=False):
                            st.json(result.get("tables", []))
                        with st.expander("Plan", expanded=False):
                            st.json(result.get("plan", {}))
                        if result.get("errors"):
                            st.error("Errors detected")
                            st.json(result.get("errors"))
            except Exception as e:
                st.error(f"Error calling API: {e}")

st.sidebar.markdown("---")
st.sidebar.write("Usage:")
st.sidebar.code(
    """
# 1) Start API with auto-reload
uvicorn reportsmith.api.server:app --reload

# 2) Start UI (auto-reloads on save)
streamlit run src/reportsmith/ui/app.py
    """
)
