from __future__ import annotations

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Memory Inspector", layout="wide")
st.title("Memory Inspector")

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page")
    st.stop()

owner_id = st.text_input("Owner ID")
if st.button("Inspect memory", type="primary"):
    try:
        memories = request("GET", "/admin/memory", token=token, params={"owner_id": owner_id})
        if not memories:
            st.info("No active memory entries")
        for memory in memories:
            st.write(
                {
                    "id": memory["id"],
                    "owner_id": memory["owner_id"],
                    "content": memory["content"],
                    "source": memory["source"],
                    "created_at": memory["created_at"],
                }
            )
    except ApiError as exc:
        st.error(exc.message)
