/* eslint-disable no-unused-vars, react-refresh/only-export-components */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

const TOOL_LABELS = {
  triage: "Triage",
  rag_search: "Docs",
  write_memory: "Remember",
  classify_issue: "Classify",
  summarize_issue: "Summarize",
  extract_entities: "Entities",
};

const STATE = {
  MISSING_ID: "missing_id",
  WAITING: "waiting",
  CONNECTING: "connecting",
  READY: "ready",
  ERROR: "error",
};

const STATE_LABELS = {
  [STATE.MISSING_ID]: "Missing widget id",
  [STATE.WAITING]: "Waiting for host identity",
  [STATE.CONNECTING]: "Connecting",
  [STATE.READY]: "Ready",
  [STATE.ERROR]: "Connection error",
};

function parseConfig() {
  const params = new URLSearchParams(window.location.search);
  const rawConfig = params.get("config");
  let config = {};
  if (rawConfig) {
    try {
      config = JSON.parse(rawConfig);
    } catch {
      config = {};
    }
  }
  return {
    widgetId: params.get("widget_id") || "",
    hostToken: params.get("host_token") || "",
    config,
  };
}

async function apiRequest(path, { method = "GET", token, body } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok) {
    throw new Error(payload?.error?.message || "Request failed.");
  }
  return payload;
}

function App() {
  const panelRef = useRef(null);
  const threadRef = useRef(null);
  const inputRef = useRef(null);

  const { widgetId, hostToken: initialHostToken, config } = useMemo(parseConfig, []);
  const enabledTools = config.enabled_tools?.length ? config.enabled_tools : ["triage"];

  const greetingText = config.greeting || "How can I help with this project?";

  const [hostToken, setHostToken] = useState(initialHostToken);
  const [accessToken, setAccessToken] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Ask about an issue, the docs, or something I should remember.",
    },
  ]);
  const [state, setState] = useState(widgetId ? STATE.WAITING : STATE.MISSING_ID);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [draft, setDraft] = useState("");

  const theme = useMemo(
    () => ({
      color: config.theme?.color || "#0f172a",
      background: config.theme?.background || "#ffffff",
      accent: config.theme?.accent || "#2563eb",
      fontFamily: config.theme?.fontFamily || "Inter, system-ui, sans-serif",
    }),
    [config],
  );

  useEffect(() => {
    const sendResize = () => {
      const height = panelRef.current?.scrollHeight || document.body.scrollHeight;
      window.parent.postMessage({ type: "copilot:resize", height: height + 16 }, "*");
    };
    sendResize();
    window.addEventListener("resize", sendResize);
    return () => window.removeEventListener("resize", sendResize);
  }, [messages, state, isSending]);

  useEffect(() => {
    const onMessage = (event) => {
      if (!event.data || event.data.type !== "copilot:host-token") return;
      setHostToken(event.data.host_token || "");
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function createSession() {
      if (!widgetId || !hostToken || accessToken || sessionId) return;
      setState(STATE.CONNECTING);
      setErrorMessage("");
      try {
        const widgetSession = await apiRequest("/widget/session", {
          method: "POST",
          body: { widget_id: widgetId, host_token: hostToken },
        });
        if (cancelled) return;
        setAccessToken(widgetSession.access_token);
        const chatSession = await apiRequest("/chat/sessions", {
          method: "POST",
          token: widgetSession.access_token,
        });
        if (cancelled) return;
        setSessionId(chatSession.session_id);
        setState(STATE.READY);
      } catch (error) {
        if (cancelled) return;
        setState(STATE.ERROR);
        setErrorMessage(error.message || "Widget authentication failed.");
      }
    }
    createSession();
    return () => {
      cancelled = true;
    };
  }, [accessToken, hostToken, sessionId, widgetId]);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  async function send(content) {
    if (!content || !accessToken || !sessionId || isSending) return;
    setIsSending(true);
    setMessages((current) => [...current, { role: "user", content }]);
    setDraft("");
    try {
      const response = await apiRequest(`/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        token: accessToken,
        body: { content },
      });
      const assistant = response?.message || {};
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: assistant.content || "I received your message.",
          toolCalls: assistant.tool_calls || [],
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error.message || "The copilot is temporarily unavailable.",
          error: true,
        },
      ]);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    send(draft.trim());
  }

  const composerDisabled = state !== STATE.READY || isSending;
  const composerPlaceholder = state === STATE.READY ? "Ask the copilot" : STATE_LABELS[state];

  return (
    <div
      ref={panelRef}
      className="copilot-shell"
      style={{
        "--copilot-color": theme.color,
        "--copilot-background": theme.background,
        "--copilot-accent": theme.accent,
        fontFamily: theme.fontFamily,
      }}
      data-widget-id={widgetId}
    >
      <header className="copilot-header">
        <div className="copilot-header-text">
          <p className="copilot-kicker">Maintainer&apos;s Copilot</p>
          <h1 className="copilot-title">{greetingText}</h1>
        </div>
        <div
          className={`copilot-status copilot-status-${state}`}
          role="status"
          aria-live="polite"
        >
          <span className="copilot-status-dot" aria-hidden="true" />
          <span className="copilot-status-label">{STATE_LABELS[state]}</span>
        </div>
      </header>

      {enabledTools.length > 0 ? (
        <section className="copilot-tools" aria-label="Enabled tools">
          {enabledTools.map((tool) => (
            <span key={tool} className="copilot-tool-chip">
              {TOOL_LABELS[tool] || tool}
            </span>
          ))}
        </section>
      ) : null}

      <section ref={threadRef} className="copilot-thread" aria-live="polite">
        {messages.map((item, index) => (
          <MessageBubble key={`${item.role}-${index}`} message={item} />
        ))}
        {isSending ? <TypingBubble /> : null}
      </section>

      {state === STATE.ERROR ? (
        <p className="copilot-banner copilot-banner-error" role="alert">
          {errorMessage || "The copilot is unavailable. Please retry."}
        </p>
      ) : null}

      <form className="copilot-composer" onSubmit={onSubmit}>
        <input
          ref={inputRef}
          className="copilot-composer-input"
          name="message"
          placeholder={composerPlaceholder}
          aria-label="Message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={composerDisabled}
          autoComplete="off"
        />
        <button
          type="submit"
          className="copilot-composer-send"
          disabled={composerDisabled || !draft.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg
      className="copilot-tool-call-icon"
      viewBox="0 0 16 16"
      width="10"
      height="10"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M3.5 8.5l3 3 6-7"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg
      className="copilot-tool-call-icon"
      viewBox="0 0 16 16"
      width="10"
      height="10"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M4 4l8 8M12 4l-8 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MessageBubble({ message }) {
  const roleClass = message.role === "user" ? "user" : "assistant";
  const errorClass = message.error ? " copilot-message-error" : "";
  return (
    <div className={`copilot-message copilot-message-${roleClass}${errorClass}`}>
      <p className="copilot-message-content">{message.content}</p>
      {message.toolCalls?.length ? (
        <div className="copilot-tool-calls" aria-label="Tool activity">
          {message.toolCalls.map((call, index) => (
            <span
              key={`${call.name}-${index}`}
              className={`copilot-tool-call ${call.ok ? "ok" : "fail"}`}
              title={call.note || undefined}
            >
              {call.ok ? <CheckIcon /> : <CrossIcon />}
              <span>{TOOL_LABELS[call.name] || call.name}</span>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TypingBubble() {
  return (
    <div
      className="copilot-message copilot-message-assistant copilot-message-typing"
      aria-label="Assistant is typing"
    >
      <span className="copilot-typing-dot" />
      <span className="copilot-typing-dot" />
      <span className="copilot-typing-dot" />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
