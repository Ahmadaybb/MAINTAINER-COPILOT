from __future__ import annotations

import streamlit as st

from api_client import API_BASE_URL, ApiError, login


st.set_page_config(
    page_title="Maintainer's Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
)


_TOKENS_CSS = """
:root {
  /* Semantic */
  --c-primary: #2563eb;
  --c-primary-hover: #1d4ed8;
  --c-primary-soft: #eff6ff;
  --c-accent: #d97706;
  --c-accent-soft: #fef3c7;
  --c-success: #15803d;
  --c-success-soft: #dcfce7;
  --c-warning: #b45309;
  --c-warning-soft: #fef3c7;
  --c-danger: #b91c1c;
  --c-danger-soft: #fee2e2;

  /* Surfaces */
  --c-surface-0: #ffffff;
  --c-surface-1: #e8eef5;
  --c-surface-2: #dbe4ee;
  --c-sidebar-bg: #d6dfeb;

  /* Borders */
  --c-border-subtle: rgba(15, 23, 42, 0.06);
  --c-border: rgba(15, 23, 42, 0.10);
  --c-border-strong: rgba(15, 23, 42, 0.16);

  /* Text */
  --c-text: #0f172a;
  --c-text-muted: #475569;
  --c-text-subtle: #94a3b8;
  --c-text-on-primary: #ffffff;

  /* Elevation */
  --c-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --c-shadow-md: 0 4px 12px rgba(15, 23, 42, 0.06);
}
"""


_BASE_STYLE = f"""
<style>
{_TOKENS_CSS}

  .stApp {{
    background: var(--c-surface-1);
  }}
  .block-container {{
    padding-top: 1.6rem;
    padding-bottom: 2rem;
    max-width: 1240px;
  }}

  section[data-testid="stSidebar"] {{
    background: var(--c-sidebar-bg);
    border-right: 1px solid var(--c-border);
  }}
  section[data-testid="stSidebar"] .stMarkdown h3 {{
    font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--c-text-muted); margin: 0 0 6px;
  }}

  h1, h2, h3 {{ color: var(--c-text); letter-spacing: -0.005em; }}
  div[data-testid="stCaptionContainer"] p {{ color: var(--c-text-muted); }}

  .copilot-page-kicker {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--c-primary); margin: 0 0 4px;
  }}

  .copilot-card {{
    border: 1px solid var(--c-border);
    border-left: 3px solid var(--c-primary);
    border-radius: 8px;
    padding: 14px 16px;
    background: var(--c-surface-0);
    box-shadow: var(--c-shadow-sm);
    height: 100%;
  }}
  .copilot-card h4 {{
    margin: 0 0 6px; font-size: 14px; font-weight: 600;
    color: var(--c-text);
  }}
  .copilot-card p {{
    margin: 0; font-size: 13px; color: var(--c-text-muted); line-height: 1.5;
  }}

  .copilot-meta {{
    font-size: 11px; color: var(--c-text-muted);
  }}
  .copilot-meta code {{
    background: var(--c-surface-2);
    color: var(--c-text);
    padding: 1px 6px; border-radius: 4px;
    font-size: 11px;
  }}
</style>
"""


st.markdown(_BASE_STYLE, unsafe_allow_html=True)


def _is_signed_in() -> bool:
    return bool(st.session_state.get("access_token"))


with st.sidebar:
    st.markdown("### Session")
    if _is_signed_in():
        st.success("Signed in")
        st.markdown(
            f"<div class='copilot-meta'>API <code>{API_BASE_URL}</code></div>",
            unsafe_allow_html=True,
        )
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("access_token", None)
            st.rerun()
    else:
        with st.form("sign_in_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="maintainer@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Sign in", use_container_width=True, type="primary"
            )
        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                try:
                    st.session_state["access_token"] = login(email, password)
                    st.rerun()
                except ApiError as exc:
                    st.error(exc.message)
        st.markdown(
            f"<div class='copilot-meta'>API <code>{API_BASE_URL}</code></div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### Pages")
    st.caption("Use the menu above the divider to switch pages.")


st.markdown(
    "<p class='copilot-page-kicker'>Maintainer's Copilot</p>", unsafe_allow_html=True
)
st.title("Console")
st.caption(
    "Authenticated triage, grounded Q&A, memory tools, and embeddable widget configuration."
)

if _is_signed_in():
    cols = st.columns(3, gap="small")
    cards = [
        (
            "Widget Config",
            "Create and edit embeddable widgets. Configure theme, allowed origins, "
            "and enabled tools, then copy the one-line embed snippet.",
        ),
        (
            "Memory Inspector",
            "Look up a maintainer's active long-term memory entries. "
            "Soft-deleted and superseded entries are excluded.",
        ),
        (
            "Chat",
            "Exercise the copilot end-to-end: triage a pasted issue, "
            "ask a grounded docs question, save a fact, or run all three.",
        ),
    ]
    for col, (title, body) in zip(cols, cards):
        with col:
            st.markdown(
                f"<div class='copilot-card'><h4>{title}</h4><p>{body}</p></div>",
                unsafe_allow_html=True,
            )
    st.write("")
    st.caption("Open a page from the sidebar menu to begin.")
else:
    st.info("Sign in from the sidebar to start using the copilot.")
    st.markdown(
        "- **Widget Config** — create embeddable widget configs and copy the embed snippet.\n"
        "- **Memory Inspector** — review a maintainer's active long-term memory.\n"
        "- **Chat** — exercise triage, RAG, and memory through the copilot itself."
    )
