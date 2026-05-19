/* eslint-disable no-unused-vars, react-refresh/only-export-components */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const toolLabels = {
  triage: "Triage",
  rag_search: "Docs",
  write_memory: "Remember",
  classify_issue: "Classify",
  summarize_issue: "Summarize",
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
  return { widgetId: params.get("widget_id") || "", config };
}

function App() {
  const panelRef = useRef(null);
  const { widgetId, config } = useMemo(parseConfig, []);
  const enabledTools = config.enabled_tools?.length ? config.enabled_tools : ["triage"];
  const [message, setMessage] = useState("");
  const [hasHostToken, setHasHostToken] = useState(false);
  const theme = {
    color: config.theme?.color || "#0f172a",
    background: config.theme?.background || "#ffffff",
    accent: config.theme?.accent || "#2563eb",
    fontFamily: config.theme?.fontFamily || "Inter, system-ui, sans-serif",
  };

  useEffect(() => {
    const sendResize = () => {
      const height = panelRef.current?.scrollHeight || document.body.scrollHeight;
      window.parent.postMessage({ type: "copilot:resize", height: height + 24 }, "*");
    };
    sendResize();
    window.addEventListener("resize", sendResize);
    return () => window.removeEventListener("resize", sendResize);
  }, [message]);

  useEffect(() => {
    const onMessage = (event) => {
      if (!event.data || event.data.type !== "copilot:host-token") return;
      setHasHostToken(Boolean(event.data.host_token));
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

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
        <div>
          <p className="copilot-kicker">Maintainer&apos;s Copilot</p>
          <h1>{config.greeting || "How can I help triage this project?"}</h1>
        </div>
        <span className={hasHostToken ? "copilot-status ready" : "copilot-status"} />
      </header>

      <section className="copilot-tools" aria-label="Enabled tools">
        {enabledTools.map((tool) => (
          <button key={tool} type="button">
            {toolLabels[tool] || tool}
          </button>
        ))}
      </section>

      <section className="copilot-thread" aria-live="polite">
        <p className="assistant-message">Ask about an issue, docs, or a decision I should remember.</p>
        {message ? <p className="user-message">{message}</p> : null}
      </section>

      <form
        className="copilot-composer"
        onSubmit={(event) => {
          event.preventDefault();
          const input = event.currentTarget.elements.namedItem("message");
          setMessage(input.value.trim());
          input.value = "";
        }}
      >
        <input name="message" placeholder="Ask the copilot" aria-label="Message" />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
