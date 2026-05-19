from __future__ import annotations

import json

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Widget Config", layout="wide")
st.title("Widget Config")

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page")
    st.stop()

left, right = st.columns([1, 1])

with left:
    st.subheader("Create")
    name = st.text_input("Name", value="Project widget")
    greeting = st.text_input("Greeting", value="Ask about this project")
    origins = st.text_area("Allowed origins", value="http://localhost:8080")
    tools = st.multiselect(
        "Enabled tools",
        ["triage", "rag_search", "write_memory", "classify_issue", "summarize_issue"],
        default=["triage", "rag_search", "write_memory"],
    )
    theme_raw = st.text_area(
        "Theme JSON",
        value=json.dumps(
            {
                "color": "#0f172a",
                "background": "#ffffff",
                "accent": "#2563eb",
                "fontFamily": "Inter, system-ui, sans-serif",
            },
            indent=2,
        ),
        height=160,
    )
    verify_key = st.text_input("Host token verify key", type="password")
    if st.button("Create widget", type="primary"):
        try:
            payload = {
                "name": name,
                "theme": json.loads(theme_raw),
                "allowed_origins": [line.strip() for line in origins.splitlines() if line.strip()],
                "greeting": greeting,
                "enabled_tools": tools,
                "host_token_verify_key": verify_key,
            }
            st.session_state["selected_widget"] = request("POST", "/admin/widgets", token=token, json=payload)
            st.success("Widget saved")
        except (ApiError, ValueError) as exc:
            st.error(getattr(exc, "message", "Theme JSON is invalid."))

with right:
    st.subheader("Saved Widgets")
    try:
        widgets = request("GET", "/admin/widgets", token=token)
    except ApiError as exc:
        st.error(exc.message)
        widgets = []
    for widget in widgets:
        with st.expander(widget["name"]):
            st.code(widget["embed_snippet"], language="html")
            for warning in widget.get("warnings", []):
                st.warning(warning)
            st.json(
                {
                    "id": widget["id"],
                    "greeting": widget["greeting"],
                    "allowed_origins": widget["allowed_origins"],
                    "enabled_tools": widget["enabled_tools"],
                }
            )
