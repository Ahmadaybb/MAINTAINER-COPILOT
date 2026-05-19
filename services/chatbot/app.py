from __future__ import annotations

import streamlit as st

from api_client import ApiError, login


st.set_page_config(page_title="Maintainer's Copilot", layout="wide")

st.title("Maintainer's Copilot")

with st.sidebar:
    st.header("Session")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        try:
            st.session_state["access_token"] = login(email, password)
            st.success("Signed in")
        except ApiError as exc:
            st.error(exc.message)
    if st.button("Sign out"):
        st.session_state.pop("access_token", None)

token = st.session_state.get("access_token")
if token:
    st.success("Connected to API")
else:
    st.warning("Sign in to continue")
