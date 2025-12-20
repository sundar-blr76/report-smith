import json
import time
from typing import Any, Dict, Optional

import requests
import streamlit as st

from reportsmith.ui.json_viewer import render_json_in_expander

st.set_page_config(page_title="ReportSmith UI", page_icon="📊", layout="wide")

# Sidebar configuration
st.sidebar.title("Settings")
api_base: str = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
timeout_s: int = st.sidebar.number_input(
    "Timeout (seconds)", min_value=1, max_value=900, value=600  # 10 minutes default
)

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
st.caption(
    "Enter a natural language question, send to the API, and view structured JSON output."
)


# Sample queries designed to trigger KG navigation and LLM refinement
samples = [
    # Triggers joins: funds → fund_manager_assignments → fund_managers; time bucketing; ambiguous term "equity products"
    "For equity products, show total fees by month for the last 12 months, only for funds managed by top-rated managers (performance_rating >= 4)",
    # Triggers clients/accounts ↔ fee_transactions ↔ funds; time filter Q1; dimension filter
    "List the top 5 clients by total fees paid on bond funds in Q1 2025",
    # Triggers metric mapping (AUM) + comparison across categories + quarterly grouping
    "Compare average AUM and total fees between equity and bond funds over 2024; return results by quarter",
    # Triggers path via account_fund_subscriptions and transactions range
    "Show daily transactions and fees for account 12345 between 2025-01-01 and 2025-01-31 (join through subscriptions if needed)",
    # Triggers multi-hop join and filters on metrics and managers
    "Find funds with AUM over 100M but total fees under 1M in 2024; include fund manager names",
    # Local mappings should catch these precisely
    "Show AUM for all equity funds",
    "List fees for TruePotential clients",
    "What's the total balance for institutional investors?",
    # LLM handles variations
    "I need the managed assets for stock portfolios",
    "Show me charges for TP customers",
    # Complex queries need both
    "Compare AUM between conservative and aggressive funds",
    "What are the average fees by fund type for all our retail investors?",
]

with st.expander("Sample queries (graph + LLM refinement)", expanded=True):
    # Add a "Select a sample query" option at the beginning
    query_options = ["Select a sample query..."] + samples
    selected = st.selectbox(
        "Choose a sample query:",
        options=query_options,
        index=0,
        key="sample_query_selector"
    )
    if selected != "Select a sample query...":
        st.session_state["rs_sample_query"] = selected

with st.form("query_form"):
    default_q = st.session_state.get("rs_sample_query") or ""
    question = st.text_area(
        "Question",
        value=default_q,
        placeholder="Show monthly fees for all equity funds",
        height=100,
    )
    app_id = st.text_input("App ID (optional)", value="")
    submitted = st.form_submit_button("Send Query")
    use_streaming = st.checkbox("Stream Response", value=True)

def render_query_results(data: Dict[str, Any]):
    """Helper to render rich query results (Table, SQL, JSON)"""
    # Extract result data
    result = data.get("data", {}) if isinstance(data, dict) else {}

    # Display query results in a table if available
    if result and result.get("result"):
        result_data = result["result"]
        execution = result_data.get("execution")

        if execution:
            if execution.get("error"):
                st.error(f"Query Execution Failed: {execution.get('error')}")
            else:
                st.success("Query executed successfully!")

                # Display results in a data table
                rows = execution.get("rows", [])
                columns = execution.get("columns", [])
                row_count = execution.get("row_count", 0)
                truncated = execution.get("truncated", False)

                if rows:
                    import pandas as pd

                    df = pd.DataFrame(rows, columns=columns)
                    
                    # Format economic/financial fields with thousand separators
                    economic_fields = ['fee_amount', 'fees', 'balance', 'total_balance', 
                                       'available_balance', 'aum_value', 'total_aum', 'aum',
                                       'transaction_amount', 'nav_per_share', 'minimum_investment',
                                       'amount', 'value', 'price', 'cost']
                    
                    # Build column config for formatting
                    column_config = {}
                    for col in df.columns:
                        col_lower = col.lower()
                        # Check if column name contains any economic field keywords
                        if any(field in col_lower for field in economic_fields):
                            # Convert to numeric if needed
                            if df[col].dtype == 'object':
                                try:
                                    df[col] = pd.to_numeric(df[col], errors='ignore')
                                except:
                                    pass
                            
                            if pd.api.types.is_numeric_dtype(df[col]):
                                column_config[col] = st.column_config.NumberColumn(
                                    col,
                                    format="%.2f"
                                )

                    st.subheader(
                        f"Query Results ({row_count} rows{' - truncated' if truncated else ''})"
                    )
                    
                    # Debug info
                    if column_config:
                        st.caption(f"Formatted columns: {', '.join(column_config.keys())}")
                    
                    st.dataframe(
                        df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=column_config if column_config else None
                    )

                    # Download as CSV
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("Query executed successfully but returned no rows.")

        # Show SQL query
        sql_data = result_data.get("sql")
        if sql_data and sql_data.get("sql"):
            with st.expander("Generated SQL", expanded=False):
                st.code(sql_data.get("sql"), language="sql")
                if sql_data.get("explanation"):
                    st.caption("Explanation:")
                    st.text(sql_data.get("explanation"))

    # Convenience views
    if result:
        render_json_in_expander(
            result.get("intent", {}), "Intent", key="intent_json", expanded=False, height=250
        )
        render_json_in_expander(
            result.get("entities", []), "Entities", key="entities_json", expanded=False, height=300
        )
        render_json_in_expander(
            result.get("tables", []), "Tables", key="tables_json", expanded=False, height=200
        )
        render_json_in_expander(
            result.get("plan", {}), "Plan", key="plan_json", expanded=False, height=300
        )
        with st.expander("Timings", expanded=False):
            timings = result.get("timings_ms", {})
            if timings:
                import pandas as pd
                df_timings = pd.DataFrame(
                    [{"Stage": k.replace("_ms", ""), "Time (ms)": v} for k, v in timings.items()]
                )
                st.dataframe(df_timings, hide_index=True)
        render_json_in_expander(
            result.get("llm_summaries", []), "LLM Summaries", key="llm_summaries_json", expanded=False, height=300
        )
        render_json_in_expander(
            data, "Full Response JSON", key="full_response_json", expanded=False, height=500
        )
        if result.get("errors"):
            st.error("Errors detected")
            render_json_in_expander(
                result.get("errors"), "Errors", key="errors_json", expanded=True, height=300
            )

if submitted:
    if not question.strip():
        st.warning("Please enter a question.")
    elif not ready_ok:
        st.warning("API is not ready yet. Please wait a few seconds and try again.")
    else:
        # Standard non-streaming path
        if not use_streaming:
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
                        try:
                            body = resp.json()
                            detail = body.get("detail", body)
                        except Exception:
                            detail = resp.text
                        st.error(f"Request failed: {detail}")
                    else:
                        render_query_results(resp.json())
                except Exception as e:
                    st.error(f"Error calling API: {e}")
        
        # Streaming path
        else:
            # Container for live updates
            status_container = st.container()
            
            # Keep track of events
            steps_data = []  # List of dicts: {name, status, duration, state}
            
            # Create a placeholder for the timeline
            timeline_ph = status_container.empty()
            
            # Placeholder for final results
            results_ph = st.empty()

            def render_timeline():
                with timeline_ph.container():
                    st.markdown("### Execution Timeline")
                    for step in steps_data:
                        name = step['name']
                        duration = step.get('duration_ms', 0)
                        status = step['status']
                        
                        if status == "running":
                            st.info(f"⏳ **{name}** running...")
                        elif status == "done":
                            label = f"✅ **{name}** ({duration:.0f}ms)"
                            with st.expander(label, expanded=False):
                                if step.get('state'):
                                    st.json(step['state'])
                        elif status == "error":
                            st.error(f"❌ **{name}** failed: {step.get('error')}")

            try:
                with requests.get(
                    f"{api_base}/query/stream",
                    params={"question": question},
                    stream=True,
                    timeout=timeout_s,
                ) as r:
                    r.raise_for_status()
                    
                    import json as _json
                    
                    # Process the stream
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        if line.startswith("data: "):
                            obj = _json.loads(line[6:])
                            evt = obj.get("event")
                            payload = obj.get("payload") or {}
                            
                            if evt == "node_start":
                                name = payload.get("name")
                                steps_data.append({"name": name, "status": "running"})
                                render_timeline()
                                
                            elif evt == "node_end":
                                name = payload.get("name")
                                duration = payload.get("duration_ms", 0)
                                state = payload.get("state")
                                
                                # Find the running step and mark done
                                for s in reversed(steps_data):
                                    if s["name"] == name and s["status"] == "running":
                                        s["status"] = "done"
                                        s["duration_ms"] = duration
                                        s["state"] = state
                                        break
                                render_timeline()
                                
                            elif evt == "error":
                                st.error(f"Streaming error: {payload}")
                                
                            elif evt == "result":
                                st.success("Orchestration Complete!")
                                # Re-construct a "QueryResponse" like dict to reuse render_query_results
                                final_state = payload.get("state", {})
                                # Wrap in {data: {result: ...}} structure expected by render_query_results
                                # Note: 'result' key in final_state corresponds to the actual query answer/execution
                                
                                # We need to map QueryState fields to the dictionary structure render_query_results expects
                                # render function expects: data -> {result: {execution: ...}, sql: ...}
                                # QueryState has: .result, .sql, .plan etc.
                                
                                # Re-structure for the renderer
                                response_wrapper = {
                                    "data": {
                                        # QueryState.result contains 'execution' etc.
                                        "result": final_state.get("result"), 
                                        "intent": final_state.get("intent"),
                                        "entities": final_state.get("entities"),
                                        "tables": final_state.get("tables"),
                                        "plan": final_state.get("plan"),
                                        "errors": final_state.get("errors"),
                                        "timings_ms": final_state.get("timings"),
                                        "llm_summaries": final_state.get("llm_summaries"),
                                        "llm_usage": final_state.get("llm_usage")
                                    }
                                }
                                
                                with results_ph.container():
                                    st.markdown("---")
                                    render_query_results(response_wrapper)

            except Exception as e:
                st.error(f"Streaming error: {e}")

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

