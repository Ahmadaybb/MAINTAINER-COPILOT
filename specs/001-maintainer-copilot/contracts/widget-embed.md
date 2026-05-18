# Contract: Embeddable Widget

## Embed snippet (single script tag — FR-020/SC-006)

```html
<script src="https://copilot.example.com/widget.js" data-widget-id="WID" async></script>
```

## Loader behavior (`/widget.js`)

1. Reads `data-widget-id`.
2. `GET /api/v1/widgets/{id}/config` → `{ theme, greeting, enabled_tools }`.
3. Injects an `<iframe>` pointing at the widget bundle, styled per `theme`.
4. The iframe and the bundled JS are one Vite build artifact (single JS file).

## Origin allowlist enforcement (US8 / FR-022 — browser-enforced)

For each `WidgetConfig`:
- **CSP**: responses serving the widget set `Content-Security-Policy: frame-ancestors <allowed_origins>`.
  Non-allowlisted host → browser refuses to render the iframe (not a server-only check).
- **CORS**: `/widgets/{id}/config` and `/widget/session` send
  `Access-Control-Allow-Origin` only for an allowlisted `Origin`.
- Empty `allowed_origins` ⇒ `frame-ancestors 'none'` (loads nowhere; admin warned, FR-026).

## Authentication handoff (US7/Q2 / FR-030 / D7)

```
host page (already authenticates its user)
  → mints short-lived signed token (key paired with WidgetConfig.host_token_verify_key)
  → widget POST /api/v1/widget/session { widget_id, host_token }
  → api verifies signature+exp against widget config → returns scoped JWT
```
Missing / malformed / expired `host_token` ⇒ 401, generic message, no diagnostics. No copilot
login UI is ever shown inside the iframe.

## Runtime messaging

- `postMessage` from iframe → host: `{ type: "copilot:resize", height }` for responsive sizing.
- Host → iframe messages are ignored unless `event.origin` ∈ allowlist.

## Tool exposure

Only `enabled_tools` from the widget config are offered in that embed (FR-021); others are
absent from the tool list sent to the LLM.
