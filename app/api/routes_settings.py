from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import reload_settings
from app.core.settings_catalog import build_settings_schema
from app.core.settings_manager import build_settings_snapshot, render_settings_page, save_managed_settings


router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(saved: int = 0) -> HTMLResponse:
    message = None
    if saved:
        message = "配置已写入 .env。涉及已初始化的全局对象时，请重启服务以确保全部生效。"
    return HTMLResponse(render_settings_page(message=message))


@router.post("/settings", include_in_schema=False)
async def save_settings_form(request: Request) -> RedirectResponse:
    form = await request.form()
    save_managed_settings(dict(form))
    reload_settings()
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.get("/api/v1/settings/schema", include_in_schema=True)
def settings_schema() -> dict[str, Any]:
    return build_settings_schema()


@router.get("/api/v1/settings/state", include_in_schema=True)
def settings_state() -> dict[str, Any]:
    return build_settings_snapshot()


@router.post("/api/v1/settings", include_in_schema=True)
def save_settings_api(payload: dict[str, Any]) -> dict[str, Any]:
    save_managed_settings(payload)
    reload_settings()
    return build_settings_snapshot(message="配置已写入 .env。")