from __future__ import annotations

from typing import Annotated, Any
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import PlainTextResponse

from app.domain.widget import PublicWidgetConfig, WidgetSessionRequest, WidgetSessionResponse
from app.services.widget_config_service import public_widget_config, sign_host_token, widget_origin_policy_headers

router = APIRouter(tags=["widgets"])


def get_widget_config_service() -> Any:
    from app.services.widget_config_service import WidgetConfigService

    return WidgetConfigService()


@router.get("/api/v1/widgets/{widget_id}/config", response_model=PublicWidgetConfig)
async def get_widget_config(
    widget_id: UUID,
    response: Response,
    service: Annotated[Any, Depends(get_widget_config_service)],
    origin: Annotated[str | None, Header()] = None,
) -> PublicWidgetConfig:
    config = service.get(widget_id)
    for header, value in widget_origin_policy_headers(
        allowed_origins=config.allowed_origins,
        request_origin=origin,
    ).items():
        response.headers[header] = value
    return public_widget_config(config)


async def _create_widget_session(
    payload: WidgetSessionRequest,
    response: Response,
    service: Any,
    origin: str | None,
) -> WidgetSessionResponse:
    config = service.get(payload.widget_id)
    for header, value in widget_origin_policy_headers(
        allowed_origins=config.allowed_origins,
        request_origin=origin,
    ).items():
        response.headers[header] = value
    return service.create_widget_session(payload)


@router.post("/api/v1/widget/session", response_model=WidgetSessionResponse)
async def create_widget_session(
    payload: WidgetSessionRequest,
    response: Response,
    service: Annotated[Any, Depends(get_widget_config_service)],
    origin: Annotated[str | None, Header()] = None,
) -> WidgetSessionResponse:
    return await _create_widget_session(payload, response, service, origin)


@router.get("/api/v1/widgets/{widget_id}/demo-host-token")
async def demo_host_token(
    widget_id: UUID,
    service: Annotated[Any, Depends(get_widget_config_service)],
) -> dict[str, str]:
    config = service.get(widget_id)
    subject = uuid4()
    token = sign_host_token(
        payload={
            "sub": str(subject),
            "email": f"widget-{subject}@example.com",
            "widget_id": str(widget_id),
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        },
        verify_key=config.host_token_verify_key,
    )
    return {"host_token": token}


@router.post("/widget/session", response_model=WidgetSessionResponse)
async def create_widget_session_compat(
    payload: WidgetSessionRequest,
    response: Response,
    service: Annotated[Any, Depends(get_widget_config_service)],
    origin: Annotated[str | None, Header()] = None,
) -> WidgetSessionResponse:
    return await _create_widget_session(payload, response, service, origin)


@router.get("/widget.js", response_class=PlainTextResponse)
async def widget_loader() -> PlainTextResponse:
    return PlainTextResponse(WIDGET_LOADER_JS, media_type="application/javascript")


WIDGET_LOADER_JS = r"""
(function () {
  var script = document.currentScript;
  if (!script) return;
  var widgetId = script.getAttribute("data-widget-id");
  if (!widgetId) return;
  var baseUrl = new URL(script.src, window.location.href).origin;
  var widgetUrl = script.getAttribute("data-widget-url") || baseUrl + "/widget/index.html";
  var hostToken = script.getAttribute("data-host-token") || "";
  var useDemoHostToken = script.getAttribute("data-demo-host-token") !== "false";
  function fetchDemoHostToken() {
    if (hostToken || !useDemoHostToken) return Promise.resolve({ host_token: hostToken });
    return fetch(baseUrl + "/api/v1/widgets/" + encodeURIComponent(widgetId) + "/demo-host-token", { credentials: "omit" })
      .then(function (response) {
        if (!response.ok) return { host_token: "" };
        return response.json();
      })
      .catch(function () {
        return { host_token: "" };
      });
  }
  fetch(baseUrl + "/api/v1/widgets/" + encodeURIComponent(widgetId) + "/config", { credentials: "omit" })
    .then(function (response) {
      if (!response.ok) throw new Error("Widget config unavailable");
      return response.json();
    })
    .then(function (config) {
      return fetchDemoHostToken().then(function (tokenPayload) {
        return { config: config, hostToken: tokenPayload.host_token || hostToken };
      });
    })
    .then(function (payload) {
      var iframe = document.createElement("iframe");
      var params = new URLSearchParams();
      params.set("widget_id", widgetId);
      params.set("config", JSON.stringify(payload.config));
      if (payload.hostToken) params.set("host_token", payload.hostToken);
      iframe.src = widgetUrl + "?" + params.toString();
      iframe.title = "Maintainer's Copilot";
      iframe.style.width = "380px";
      iframe.style.maxWidth = "100%";
      iframe.style.height = "520px";
      iframe.style.border = "0";
      iframe.style.borderRadius = "8px";
      iframe.style.boxShadow = "0 16px 40px rgba(15, 23, 42, 0.18)";
      iframe.setAttribute("data-maintainer-copilot-widget", widgetId);
      script.parentNode.insertBefore(iframe, script.nextSibling);
      window.addEventListener("message", function (event) {
        if (event.source !== iframe.contentWindow) return;
        if (!event.data || event.data.type !== "copilot:resize") return;
        var height = Number(event.data.height);
        if (Number.isFinite(height) && height > 240) iframe.style.height = height + "px";
      });
    })
    .catch(function () {
      script.setAttribute("data-widget-error", "config-unavailable");
    });
})();
""".strip()
