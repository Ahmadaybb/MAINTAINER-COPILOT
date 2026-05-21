from __future__ import annotations

import json
import html

import streamlit as st

from api_client import ApiError, request


st.set_page_config(page_title="Widget Config • Copilot", layout="wide")


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
    padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1240px;
  }}
  section[data-testid="stSidebar"] {{
    background: var(--c-sidebar-bg);
    border-right: 1px solid var(--c-border);
  }}

  .copilot-page-kicker {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--c-primary); margin: 0 0 4px;
  }}

  .copilot-section-label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--c-text-muted);
    margin: 16px 0 6px;
  }}

  .copilot-preview-card {{
    border: 1px solid var(--c-border);
    border-radius: 10px;
    padding: 14px 16px;
    background: var(--c-surface-0);
    box-shadow: var(--c-shadow-sm);
  }}
  .copilot-preview-kicker {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; margin: 0 0 4px;
  }}
  .copilot-preview-title {{
    margin: 0; font-size: 15px; font-weight: 600; line-height: 1.3;
  }}

  .copilot-swatch {{
    height: 30px; border-radius: 6px;
    border: 1px solid var(--c-border);
  }}
  .copilot-swatch-label {{
    font-size: 11px; color: var(--c-text-muted); margin-top: 4px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}

  .copilot-tool-pill {{
    display: inline-block; padding: 2px 8px; margin: 2px 4px 2px 0;
    border-radius: 999px;
    background: var(--c-primary-soft);
    color: var(--c-primary);
    border: 1px solid rgba(37, 99, 235, 0.18);
    font-size: 11px;
    font-weight: 500;
  }}

  .copilot-warn-badge {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    background: var(--c-warning-soft); color: var(--c-warning);
    border: 1px solid rgba(217, 119, 6, 0.30);
    font-size: 11px; font-weight: 500;
  }}

  .copilot-meta {{ font-size: 11px; color: var(--c-text-muted); }}
  .copilot-meta code {{
    background: var(--c-surface-2); color: var(--c-text);
    padding: 1px 6px; border-radius: 4px;
  }}
</style>
"""

st.markdown(_PAGE_STYLE, unsafe_allow_html=True)

st.markdown(
    "<p class='copilot-page-kicker'>Widgets</p>", unsafe_allow_html=True
)
st.title("Widget Configuration")
st.caption(
    "Create and edit embeddable widget configs. Copy the embed snippet into a host application."
)

token = st.session_state.get("access_token")
if not token:
    st.warning("Sign in on the main page to manage widgets.")
    st.stop()


DEFAULT_THEME = {
    "color": "#0f172a",
    "background": "#ffffff",
    "accent": "#2563eb",
    "fontFamily": "Inter, system-ui, sans-serif",
}

ALL_TOOLS = [
    "triage",
    "rag_search",
    "write_memory",
    "classify_issue",
    "summarize_issue",
]


@st.cache_data(ttl=5, show_spinner=False)
def _fetch_widgets(_token: str) -> list[dict]:
    return request("GET", "/admin/widgets", token=_token) or []


def _safe_load_theme(raw: str) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, exc.msg
    if not isinstance(value, dict):
        return None, "Theme must be a JSON object."
    return value, None


tab_create, tab_saved = st.tabs(["Create", "Saved widgets"])


# ---------- Create tab ----------

with tab_create:
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(
            "<p class='copilot-section-label'>Identity</p>", unsafe_allow_html=True
        )
        name = st.text_input(
            "Name",
            value="Project widget",
            help="Internal label used to identify this widget in the admin list.",
        )
        greeting = st.text_input(
            "Greeting",
            value="Ask about this project",
            help="Shown as the first line inside the widget header.",
        )

        st.markdown(
            "<p class='copilot-section-label'>Behavior</p>", unsafe_allow_html=True
        )
        tools = st.multiselect(
            "Enabled tools",
            ALL_TOOLS,
            default=["triage", "rag_search", "write_memory"],
            help="Only these tools are exposed in the embed.",
        )

        st.markdown(
            "<p class='copilot-section-label'>Embedding</p>", unsafe_allow_html=True
        )
        origins_raw = st.text_area(
            "Allowed origins",
            value="http://localhost:8080",
            help=(
                "One origin per line (e.g. https://docs.example.com). "
                "Empty list will block all embeds."
            ),
            height=84,
        )
        verify_key = st.text_input(
            "Host token verify key",
            type="password",
            help="Shared HMAC secret used to verify host-signed identity tokens.",
        )

        st.markdown(
            "<p class='copilot-section-label'>Appearance</p>", unsafe_allow_html=True
        )
        with st.expander("Theme JSON (advanced)", expanded=False):
            theme_raw = st.text_area(
                "Theme",
                value=json.dumps(DEFAULT_THEME, indent=2),
                height=160,
                help="JSON with keys: color, background, accent, fontFamily.",
                label_visibility="collapsed",
            )

        st.write("")
        if st.button("Create widget", type="primary", use_container_width=True):
            allowed_origins = [
                line.strip() for line in origins_raw.splitlines() if line.strip()
            ]
            theme, theme_error = _safe_load_theme(theme_raw)
            if theme_error is not None:
                st.error(f"Theme JSON is invalid: {theme_error}")
            elif not verify_key:
                st.error("Host token verify key is required.")
            elif not tools:
                st.error("Select at least one tool.")
            elif not name.strip():
                st.error("Name is required.")
            else:
                payload = {
                    "name": name.strip(),
                    "theme": theme,
                    "allowed_origins": allowed_origins,
                    "greeting": greeting,
                    "enabled_tools": tools,
                    "host_token_verify_key": verify_key,
                }
                try:
                    created = request(
                        "POST", "/admin/widgets", token=token, json=payload
                    )
                    st.success(f"Created widget '{created['name']}'.")
                    st.markdown(
                        f"<div class='copilot-meta'>id <code>{created['id']}</code></div>",
                        unsafe_allow_html=True,
                    )
                    for warning in created.get("warnings", []):
                        st.warning(warning)
                    _fetch_widgets.clear()
                except ApiError as exc:
                    st.error(exc.message)

    with right:
        st.markdown(
            "<p class='copilot-section-label'>Preview</p>", unsafe_allow_html=True
        )

        preview_theme, _ = _safe_load_theme(theme_raw)
        preview_theme = preview_theme or DEFAULT_THEME

        color = preview_theme.get("color", "#0f172a")
        background = preview_theme.get("background", "#ffffff")
        accent = preview_theme.get("accent", "#2563eb")
        font_family = preview_theme.get("fontFamily", "Inter, system-ui, sans-serif")
        safe_greeting = html.escape(
            greeting or "How can I help with this project?", quote=True
        )

        st.markdown(
            f"""
            <div class='copilot-preview-card' style="
              background:{html.escape(background, quote=True)};
              color:{html.escape(color, quote=True)};
              font-family:{html.escape(font_family, quote=True)};
            ">
              <p class='copilot-preview-kicker' style="color:{html.escape(accent, quote=True)};">
                Maintainer&apos;s Copilot
              </p>
              <p class='copilot-preview-title'>{safe_greeting}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p class='copilot-section-label' style='margin-top:18px;'>Theme</p>",
            unsafe_allow_html=True,
        )
        swatch_cols = st.columns(3)
        for col, key in zip(swatch_cols, ["color", "background", "accent"]):
            value = preview_theme.get(key, "")
            with col:
                st.markdown(
                    f"""
                    <div class='copilot-swatch' style="background:{html.escape(value, quote=True)};"></div>
                    <div class='copilot-swatch-label'>{html.escape(key, quote=True)}<br>{html.escape(value, quote=True)}</div>
                    """,
                    unsafe_allow_html=True,
                )

        font_label = font_family.split(",")[0].strip() if font_family else "—"
        st.markdown(
            f"<div class='copilot-swatch-label' style='margin-top:10px;'>fontFamily — {html.escape(font_label, quote=True)}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p class='copilot-section-label' style='margin-top:18px;'>Tools</p>",
            unsafe_allow_html=True,
        )
        if tools:
            chips = "".join(
                f"<span class='copilot-tool-pill'>{html.escape(tool, quote=True)}</span>"
                for tool in tools
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.caption("None selected — widget will offer no tools.")

        st.markdown(
            "<p class='copilot-section-label' style='margin-top:18px;'>Origins</p>",
            unsafe_allow_html=True,
        )
        preview_origins = [
            line.strip() for line in origins_raw.splitlines() if line.strip()
        ]
        if preview_origins:
            st.code("\n".join(preview_origins), language="text")
        else:
            st.markdown(
                "<span class='copilot-warn-badge'>No origins — widget will load nowhere</span>",
                unsafe_allow_html=True,
            )


# ---------- Saved tab ----------

with tab_saved:
    try:
        widgets = _fetch_widgets(token)
    except ApiError as exc:
        st.error(exc.message)
        widgets = []

    if not widgets:
        st.info("No widgets configured yet. Create one in the **Create** tab.")
    else:
        st.caption(f"{len(widgets)} widget(s) configured.")
        for widget in widgets:
            warnings = widget.get("warnings") or []
            title_suffix = "  ⚠" if warnings else ""
            with st.expander(f"{widget['name']}  ·  {widget['id']}{title_suffix}", expanded=False):
                meta_cols = st.columns([2, 2, 2])
                with meta_cols[0]:
                    st.caption("Greeting")
                    st.write(widget.get("greeting") or "—")
                with meta_cols[1]:
                    st.caption("Enabled tools")
                    enabled = widget.get("enabled_tools") or []
                    if enabled:
                        st.markdown(
                            "".join(
                                f"<span class='copilot-tool-pill'>{html.escape(tool, quote=True)}</span>"
                                for tool in enabled
                            ),
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write("—")
                with meta_cols[2]:
                    st.caption("Allowed origins")
                    origins = widget.get("allowed_origins") or []
                    if origins:
                        st.code("\n".join(origins), language="text")
                    else:
                        st.markdown(
                            "<span class='copilot-warn-badge'>No origins — widget will load nowhere</span>",
                            unsafe_allow_html=True,
                        )

                st.caption("Embed snippet")
                st.code(widget["embed_snippet"], language="html")

                for warning in warnings:
                    st.warning(warning)
