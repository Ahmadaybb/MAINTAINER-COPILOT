from __future__ import annotations

import html
from datetime import datetime
from uuid import UUID

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Memory Inspector • Copilot", layout="wide")


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
    padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1100px;
  }}
  section[data-testid="stSidebar"] {{
    background: var(--c-sidebar-bg);
    border-right: 1px solid var(--c-border);
  }}

  /* This page is admin-only — kicker uses the accent (amber) hue. */
  .copilot-page-kicker {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--c-accent); margin: 0 0 4px;
  }}

  .copilot-memory-card {{
    border: 1px solid var(--c-border);
    border-left: 3px solid var(--c-primary);
    border-radius: 8px;
    padding: 12px 14px 10px;
    background: var(--c-surface-0);
    box-shadow: var(--c-shadow-sm);
    margin-bottom: 8px;
  }}
  .copilot-memory-card.is-inferred {{
    border-left-color: var(--c-text-subtle);
  }}

  .copilot-memory-content {{
    margin: 0 0 8px;
    font-size: 14px;
    line-height: 1.55;
    color: var(--c-text);
    white-space: pre-wrap;
    word-break: break-word;
  }}

  .copilot-memory-meta {{
    display: flex; flex-wrap: wrap; gap: 12px;
    font-size: 11px; color: var(--c-text-muted);
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}

  .copilot-memory-source {{
    display: inline-block; padding: 1px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 500;
    font-family: Inter, system-ui, sans-serif;
    border: 1px solid transparent;
  }}
  .copilot-memory-source-explicit {{
    background: var(--c-primary-soft); color: var(--c-primary);
    border-color: rgba(37, 99, 235, 0.18);
  }}
  .copilot-memory-source-inferred {{
    background: var(--c-surface-2); color: var(--c-text-muted);
    border-color: var(--c-border-subtle);
  }}
</style>
"""

st.markdown(_PAGE_STYLE, unsafe_allow_html=True)

st.markdown(
    "<p class='copilot-page-kicker'>Admin</p>", unsafe_allow_html=True
)
st.title("Memory Inspector")
st.caption(
    "Review a maintainer's active long-term memory entries. "
    "Soft-deleted and superseded entries are excluded."
)

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page to inspect memory.")
    st.stop()


def _format_ts(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except (TypeError, ValueError):
        return value


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


with st.form("memory_query", clear_on_submit=False):
    owner_id = st.text_input(
        "Owner ID",
        value=st.session_state.get("memory_owner_id", ""),
        help="UUID of the maintainer whose memory you want to inspect.",
        placeholder="00000000-0000-0000-0000-000000000000",
    )
    submitted = st.form_submit_button("Inspect", type="primary")

if submitted:
    owner_id = (owner_id or "").strip()
    st.session_state["memory_owner_id"] = owner_id
    if not owner_id:
        st.error("Owner ID is required.")
    elif not _is_uuid(owner_id):
        st.error("Owner ID must be a valid UUID.")
    else:
        try:
            memories = request(
                "GET",
                "/admin/memory",
                token=token,
                params={"owner_id": owner_id},
            ) or []
            st.session_state["memory_results"] = memories
            st.session_state["memory_loaded"] = True
        except ApiError as exc:
            st.error(exc.message)
            st.session_state["memory_results"] = []
            st.session_state["memory_loaded"] = True


if st.session_state.get("memory_loaded"):
    memories = st.session_state.get("memory_results") or []
    if not memories:
        st.info("No active memory entries for that owner.")
    else:
        sorted_memories = sorted(
            memories, key=lambda m: m.get("created_at") or "", reverse=True
        )
        st.caption(f"{len(sorted_memories)} active entries (newest first).")
        for memory in sorted_memories:
            content = html.escape(memory.get("content") or "—", quote=True)
            source = (memory.get("source") or "").lower() or "inferred"
            source_class = (
                "copilot-memory-source-explicit"
                if source == "explicit"
                else "copilot-memory-source-inferred"
            )
            card_modifier = "" if source == "explicit" else " is-inferred"
            memory_id = html.escape(str(memory.get("id") or ""), quote=True)
            created = html.escape(_format_ts(memory.get("created_at")), quote=True)
            st.markdown(
                f"""
                <div class='copilot-memory-card{card_modifier}'>
                  <p class='copilot-memory-content'>{content}</p>
                  <div class='copilot-memory-meta'>
                    <span class='copilot-memory-source {source_class}'>{html.escape(source, quote=True)}</span>
                    <span>created · {created}</span>
                    <span>id · {memory_id}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    st.write("")
    st.markdown(
        """
        **Getting started**

        1. Paste a maintainer's UUID into the field above.
        2. Click **Inspect** to load their active long-term memories.

        This view is admin-only. Non-admin tokens will receive a permission error.
        """
    )
