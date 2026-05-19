from __future__ import annotations

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Chat", layout="wide")
st.title("Chat")

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page")
    st.stop()

if "session_id" not in st.session_state:
    if st.button("New chat", type="primary"):
        try:
            session = request("POST", "/chat/sessions", token=token)
            st.session_state["session_id"] = session["session_id"]
            st.session_state["messages"] = []
        except ApiError as exc:
            st.error(exc.message)
    st.stop()

for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.write(message["content"])

content = st.chat_input("Message")
if content:
    st.session_state.setdefault("messages", []).append({"role": "user", "content": content})
    try:
        response = request(
            "POST",
            f"/chat/sessions/{st.session_state['session_id']}/messages",
            token=token,
            json={"content": content},
        )
        assistant = response["message"]
        st.session_state["messages"].append({"role": "assistant", "content": assistant["content"]})
        st.rerun()
    except ApiError as exc:
        st.error(exc.message)
