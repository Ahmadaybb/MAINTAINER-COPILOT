from __future__ import annotations

import html

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Chat • Copilot", layout="wide")


_TOKENS_CSS = """
:root {
  --c-primary: #2563eb;
  --c-primary-soft: #eff6ff;
  --c-accent: #d97706;
  --c-accent-soft: #fef3c7;
  --c-success: #15803d;
  --c-success-soft: #dcfce7;
  --c-warning: #b45309;
  --c-warning-soft: #fef3c7;
  --c-danger: #b91c1c;
  --c-danger-soft: #fee2e2;
  --c-surface-0: #ffffff;
  --c-surface-1: #e8eef5;
  --c-surface-2: #dbe4ee;
  --c-sidebar-bg: #d6dfeb;
  --c-border-subtle: rgba(15, 23, 42, 0.06);
  --c-border: rgba(15, 23, 42, 0.10);
  --c-border-strong: rgba(15, 23, 42, 0.16);
  --c-text: #0f172a;
  --c-text-muted: #475569;
  --c-text-subtle: #94a3b8;
  --c-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
}
"""

_PAGE_STYLE = f"""
<style>
{_TOKENS_CSS}

  .stApp {{
    background: var(--c-surface-1);
  }}
  .block-container {{
    padding-top: 1.4rem; padding-bottom: 6rem; max-width: 1100px;
  }}
  section[data-testid="stSidebar"] {{
    background: var(--c-sidebar-bg);
    border-right: 1px solid var(--c-border);
  }}
  section[data-testid="stSidebar"] .stButton button {{
    text-align: left; font-size: 12.5px; line-height: 1.4;
    padding: 8px 10px; white-space: normal; height: auto;
  }}

  .copilot-page-kicker {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--c-primary); margin: 0 0 4px;
  }}

  .copilot-session-card {{
    border: 1px solid var(--c-border);
    border-left: 3px solid var(--c-text-subtle);
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--c-surface-0);
    box-shadow: var(--c-shadow-sm);
    margin-bottom: 12px;
  }}
  .copilot-session-card.is-active {{
    border-left-color: var(--c-success);
  }}

  .copilot-session-row {{
    display: flex; align-items: center; gap: 8px;
    font-size: 12px; color: var(--c-text);
  }}
  .copilot-session-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    flex: 0 0 auto;
  }}
  .copilot-session-dot.active {{ background: var(--c-success); }}
  .copilot-session-dot.idle {{ background: var(--c-text-subtle); }}

  .copilot-session-id {{
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px; color: var(--c-text-muted);
    word-break: break-all;
    margin-top: 4px;
  }}

  .copilot-tool-line {{
    display: flex; flex-wrap: wrap; gap: 6px;
    margin-top: 6px;
  }}
  .copilot-tool-badge {{
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px; border-radius: 6px;
    font-size: 11px; font-weight: 500;
    border: 1px solid transparent;
  }}
  .copilot-tool-badge.ok {{
    background: var(--c-success-soft); color: var(--c-success);
    border-color: rgba(22, 163, 74, 0.22);
  }}
  .copilot-tool-badge.fail {{
    background: var(--c-danger-soft); color: var(--c-danger);
    border-color: rgba(185, 28, 28, 0.22);
  }}
</style>
"""

st.markdown(_PAGE_STYLE, unsafe_allow_html=True)


st.markdown(
    "<p class='copilot-page-kicker'>Copilot</p>", unsafe_allow_html=True
)
st.title("Chat")
st.caption(
    "Exercise triage, grounded Q&A, and memory through the copilot itself."
)

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page to start chatting.")
    st.stop()


EXAMPLE_PROMPTS = [
    "Triage this: TypeError in parser.py on v1.2.0 when calling parse()",
    "What docs do we have about retry policy?",
    "Remember: my preferred branch is main",
    "Summarize this issue and label it: 'CLI exits 1 when path contains spaces'",
]


def _start_session() -> bool:
    try:
        session = request("POST", "/chat/sessions", token=token)
    except ApiError as exc:
        st.error(exc.message)
        return False
    st.session_state["session_id"] = session["session_id"]
    st.session_state["messages"] = []
    return True


def _render_tool_calls(tool_calls: list[dict]) -> None:
    if not tool_calls:
        return
    parts = []
    for call in tool_calls:
        ok = bool(call.get("ok"))
        symbol = "✓" if ok else "✗"
        css = "ok" if ok else "fail"
        name = html.escape(str(call.get("name") or "tool"), quote=True)
        note = call.get("note")
        title_attr = f" title=\"{html.escape(str(note), quote=True)}\"" if note else ""
        parts.append(
            f"<span class='copilot-tool-badge {css}'{title_attr}>"
            f"{symbol} {name}</span>"
        )
    st.markdown(
        "<div class='copilot-tool-line'>" + "".join(parts) + "</div>",
        unsafe_allow_html=True,
    )


# ---------- Sidebar ----------

with st.sidebar:
    st.markdown("### Session")
    session_id = st.session_state.get("session_id")
    if session_id:
        st.markdown(
            f"""
            <div class='copilot-session-card is-active'>
              <div class='copilot-session-row'>
                <span class='copilot-session-dot active'></span>
                <span><strong>Active</strong></span>
              </div>
              <div class='copilot-session-id'>{html.escape(str(session_id), quote=True)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class='copilot-session-card'>
              <div class='copilot-session-row'>
                <span class='copilot-session-dot idle'></span>
                <span>No active session</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("New chat", use_container_width=True, type="primary"):
        if _start_session():
            st.rerun()

    if session_id and st.button("End chat", use_container_width=True):
        st.session_state.pop("session_id", None)
        st.session_state.pop("messages", None)
        st.rerun()

    st.divider()
    st.markdown("### Try")
    st.caption("One-click prompts to exercise the copilot.")
    for idx, prompt in enumerate(EXAMPLE_PROMPTS):
        if st.button(prompt, use_container_width=True, key=f"prompt-{idx}"):
            if session_id or _start_session():
                st.session_state["pending_prompt"] = prompt
                st.rerun()


# ---------- Main area ----------

if not st.session_state.get("session_id"):
    st.info("Start a new chat from the sidebar to begin.")
    st.stop()

messages = st.session_state.setdefault("messages", [])

# Replay history
for message in messages:
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["content"])
        else:
            st.write(message["content"])
        if message["role"] == "assistant":
            _render_tool_calls(message.get("tool_calls") or [])


def _send_message(content: str) -> None:
    content = (content or "").strip()
    if not content:
        return
    st.session_state["messages"].append({"role": "user", "content": content})
    with st.chat_message("user"):
        st.write(content)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Thinking…"):
            try:
                response = request(
                    "POST",
                    f"/chat/sessions/{st.session_state['session_id']}/messages",
                    token=token,
                    json={"content": content},
                )
            except ApiError as exc:
                placeholder.error(exc.message)
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": exc.message,
                        "error": True,
                        "tool_calls": [],
                    }
                )
                return

        assistant = response.get("message") or {}
        assistant_content = assistant.get("content") or "(no response)"
        tool_calls = assistant.get("tool_calls") or []
        placeholder.write(assistant_content)
        _render_tool_calls(tool_calls)
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": tool_calls,
            }
        )


# Handle pending prompt from sidebar
pending = st.session_state.pop("pending_prompt", None)
if pending:
    _send_message(pending)

user_input = st.chat_input("Message the copilot")
if user_input:
    _send_message(user_input)
