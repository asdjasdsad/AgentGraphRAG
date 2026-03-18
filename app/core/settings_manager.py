from __future__ import annotations

import ast
import json
import re
from html import escape
from typing import Any

from app.core.config import APP_ENV_PREFIX, ENV_FILE, Settings, get_settings
from app.core.settings_catalog import (
    CONFIG_FIELDS,
    PRESET_GROUP_META,
    PRESET_GROUP_ORDER,
    PRESET_GROUPS,
    SECRET_FIELD_NAMES,
    SECTION_META,
    SECTION_ORDER,
    build_config_checks,
    build_settings_schema,
    resolve_settings_values,
)


ENV_LINE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
MANAGED_ENV_KEYS = {f"{APP_ENV_PREFIX}{field.name.upper()}": field.name for field in CONFIG_FIELDS}


def env_var_name(field_name: str) -> str:
    return f"{APP_ENV_PREFIX}{field_name.upper()}"


def _as_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _decode_env_value(raw_value: str) -> str:
    text = raw_value.strip()
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return text[1:-1]
        return _as_string(parsed)
    return text


def _encode_env_value(value: str) -> str:
    normalized = value.strip()
    if normalized.lower() in {"true", "false"}:
        return normalized.lower()
    return json.dumps(value, ensure_ascii=False)


def load_managed_env_values() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        match = ENV_LINE_PATTERN.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        field_name = MANAGED_ENV_KEYS.get(key)
        if field_name:
            values[field_name] = _decode_env_value(raw_value)
    return values


def current_settings_values(settings: Settings | None = None) -> dict[str, str]:
    settings = settings or get_settings()
    env_values = load_managed_env_values()
    values: dict[str, str] = {}
    for field in CONFIG_FIELDS:
        values[field.name] = env_values.get(field.name, _as_string(getattr(settings, field.name)))
    return values


def normalize_submitted_settings(submitted: dict[str, Any]) -> dict[str, str]:
    current_values = current_settings_values()
    normalized: dict[str, str] = {}
    for field in CONFIG_FIELDS:
        raw_value = _as_string(submitted.get(field.name, "")).strip()
        if field.secret and not raw_value:
            normalized[field.name] = current_values.get(field.name, "")
            continue
        if field.required and not raw_value:
            normalized[field.name] = current_values.get(field.name, "")
            continue
        normalized[field.name] = raw_value
    return resolve_settings_values(normalized)


def save_managed_settings(submitted: dict[str, Any]) -> dict[str, str]:
    normalized = normalize_submitted_settings(submitted)
    updates = {env_var_name(field.name): normalized[field.name] for field in CONFIG_FIELDS}
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    saved_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        match = ENV_LINE_PATTERN.match(line)
        if not match:
            new_lines.append(line)
            continue
        key = match.group(1)
        if key in updates:
            new_lines.append(f"{key}={_encode_env_value(updates[key])}")
            saved_keys.add(key)
            continue
        new_lines.append(line)
    pending_keys = [key for key in updates if key not in saved_keys]
    if pending_keys:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        if not any(line.strip() == "# AgentGraphRAG managed settings" for line in new_lines):
            new_lines.append("# AgentGraphRAG managed settings")
        for key in pending_keys:
            new_lines.append(f"{key}={_encode_env_value(updates[key])}")
    ENV_FILE.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    return normalized


def _mask_value(field_name: str, value: str) -> str:
    return "******" if field_name in SECRET_FIELD_NAMES and value else value


def _build_summary(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "errors": sum(1 for item in checks if item["level"] == "error"),
        "warnings": sum(1 for item in checks if item["level"] == "warning"),
        "infos": sum(1 for item in checks if item["level"] == "info"),
        "success": sum(1 for item in checks if item["level"] == "success"),
    }


def build_settings_snapshot(message: str | None = None) -> dict[str, Any]:
    raw_values = current_settings_values()
    resolved_values = resolve_settings_values(raw_values)
    checks = build_config_checks(raw_values)
    return {
        "message": message,
        "env_file": str(ENV_FILE),
        "env_prefix": APP_ENV_PREFIX,
        "schema": build_settings_schema(),
        "summary": _build_summary(checks),
        "checks": checks,
        "values": {field.name: _mask_value(field.name, raw_values[field.name]) for field in CONFIG_FIELDS},
        "resolved_values": {field.name: _mask_value(field.name, resolved_values[field.name]) for field in CONFIG_FIELDS},
        "secret_state": {field.name: bool(raw_values.get(field.name, "")) for field in CONFIG_FIELDS if field.secret},
    }


def _render_input(field_name: str, value: str, field: Any) -> str:
    if field.options:
        options_html = []
        for option in field.options:
            selected = " selected" if value == option.value else ""
            options_html.append(f'<option value="{escape(option.value, quote=True)}"{selected}>{escape(option.label)}</option>')
        return f'<select name="{field_name}" id="{field_name}">{"".join(options_html)}</select>'
    if field.secret:
        placeholder = "已保存，留空则保留原值" if value else field.placeholder
        return f'<input type="{field.input_type}" name="{field_name}" id="{field_name}" placeholder="{escape(placeholder, quote=True)}" value="" autocomplete="off" />'
    return f'<input type="{field.input_type}" name="{field_name}" id="{field_name}" placeholder="{escape(field.placeholder, quote=True)}" value="{escape(value, quote=True)}" />'


def render_settings_page(message: str | None = None) -> str:
    raw_values = current_settings_values()
    resolved_values = resolve_settings_values(raw_values)
    checks = build_config_checks(raw_values)
    summary = _build_summary(checks)
    preset_payload = {group: {preset.key: {"defaults": preset.defaults, "key": preset.key} for preset in presets} for group, presets in PRESET_GROUPS.items()}

    preset_sections_html: list[str] = []
    for group in PRESET_GROUP_ORDER:
        title, intro = PRESET_GROUP_META[group]
        cards: list[str] = []
        for preset in PRESET_GROUPS[group]:
            docs_html = f'<a class="preset__link" href="{escape(preset.docs_url, quote=True)}" target="_blank" rel="noreferrer">{escape(preset.docs_label)}</a>' if preset.docs_url else ""
            notes_html = "".join(f"<li>{escape(note)}</li>" for note in preset.notes)
            cards.append(f'''<article class="preset"><div class="preset__top"><div><h3>{escape(preset.label)}</h3><p>{escape(preset.summary)}</p></div><button type="button" class="preset__button" onclick="applyPreset('{escape(group, quote=True)}', '{escape(preset.key, quote=True)}')">应用预设</button></div>{docs_html}<ul class="preset__notes">{notes_html}</ul></article>''')
        preset_sections_html.append(f'''<section class="card"><div class="card__title">{escape(title)}</div><p class="card__intro">{escape(intro)}</p><div class="preset-grid">{"".join(cards)}</div></section>''')

    check_cards: list[str] = []
    for check in checks:
        field_line = f'<div class="check__fields">{escape(check["field_labels"])}</div>' if check["field_labels"] else ""
        check_cards.append(f'''<article class="check check--{escape(check['level'], quote=True)}"><div class="check__title">{escape(check['title'])}</div><div class="check__message">{escape(check['message'])}</div>{field_line}</article>''')

    sections_html: list[str] = []
    for section in SECTION_ORDER:
        title, intro = SECTION_META[section]
        fields_html: list[str] = []
        for field in CONFIG_FIELDS:
            if field.section != section:
                continue
            raw_value = raw_values[field.name]
            resolved_value = resolved_values[field.name]
            auto_fill_hint = f'<div class="field__auto">保存时会自动补全为：{escape(resolved_value)}</div>' if (not raw_value and resolved_value and resolved_value != raw_value and not field.secret) else ""
            secret_state = '<span class="secret-state secret-state--set">已保存</span>' if field.secret and raw_value else '<span class="secret-state">未设置</span>' if field.secret else ''
            fields_html.append(f'''<label class="field" for="{field.name}"><div class="field__head"><span>{escape(field.label)}</span>{secret_state}</div><div class="field__env">{escape(env_var_name(field.name))}</div><div class="field__input">{_render_input(field.name, raw_value, field)}</div><div class="field__desc">{escape(field.description)}</div>{auto_fill_hint}</label>''')
        sections_html.append(f'''<section class="card"><div class="card__title">{escape(title)}</div><p class="card__intro">{escape(intro)}</p><div class="grid">{"".join(fields_html)}</div></section>''')

    template = """<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AgentGraphRAG 配置中心</title>
    <style>
      :root {
        --bg: #f4efe7;
        --bg-accent: #e9e1d5;
        --panel: rgba(255, 251, 244, 0.94);
        --line: rgba(60, 46, 34, 0.14);
        --text: #2c241d;
        --muted: #6e5d50;
        --accent: #a5512a;
        --accent-2: #1d6b5f;
        --shadow: 0 22px 70px rgba(82, 54, 25, 0.12);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "IBM Plex Sans", "Noto Sans SC", sans-serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, rgba(165, 81, 42, 0.16), transparent 26%),
          radial-gradient(circle at bottom right, rgba(29, 107, 95, 0.16), transparent 28%),
          linear-gradient(135deg, var(--bg), var(--bg-accent));
      }
      .page { max-width: 1240px; margin: 0 auto; padding: 28px 18px 48px; }
      .hero, .card { border: 1px solid var(--line); border-radius: 26px; background: var(--panel); box-shadow: var(--shadow); }
      .hero { padding: 28px; }
      .hero__eyebrow { display: inline-block; padding: 6px 10px; border-radius: 999px; background: rgba(165, 81, 42, 0.12); color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      h1 { margin: 16px 0 10px; font-size: clamp(32px, 4vw, 54px); line-height: 1.02; }
      p { margin: 0; color: var(--muted); line-height: 1.65; }
      .nav, .hero__meta, .summary, .actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .nav, .hero__meta, .summary, .actions { margin-top: 18px; }
      .nav a, .button, .save-button, .preset__button { text-decoration: none; border: 0; border-radius: 999px; padding: 12px 16px; font: inherit; font-weight: 700; cursor: pointer; background: linear-gradient(135deg, #c96f34, #8c4021); color: #fff; }
      .nav a.alt, .button.alt { background: rgba(44, 36, 29, 0.08); color: var(--text); }
      .chip { padding: 9px 12px; border-radius: 999px; background: rgba(44, 36, 29, 0.07); color: var(--muted); font-size: 13px; }
      .chip strong { color: var(--text); }
      .alert, #testResult { padding: 14px 16px; border-radius: 18px; border: 1px solid rgba(29, 107, 95, 0.22); background: rgba(29, 107, 95, 0.11); color: var(--accent-2); font-weight: 600; white-space: pre-wrap; }
      #testResult.warn { border-color: rgba(140, 93, 27, 0.22); background: rgba(140, 93, 27, 0.11); color: #8c5d1b; }
      form { margin-top: 20px; }
      .stack { display: grid; gap: 18px; margin-top: 18px; }
      .card { padding: 22px; }
      .card__title { font-size: 22px; font-weight: 700; }
      .card__intro { margin: 8px 0 0; }
      .preset-grid, .grid, .check-grid { display: grid; gap: 14px; margin-top: 18px; }
      .preset-grid, .grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
      .check-grid { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
      .preset, .check, .field { padding: 16px; border-radius: 20px; border: 1px solid rgba(44, 36, 29, 0.08); background: rgba(255, 255, 255, 0.74); }
      .preset__top { display: flex; gap: 12px; justify-content: space-between; align-items: flex-start; }
      .preset h3 { margin: 0; font-size: 18px; }
      .preset p { margin-top: 6px; }
      .preset__link { color: var(--accent-2); font-weight: 600; text-decoration: none; }
      .preset__notes { margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.55; }
      .check--error { border-color: rgba(140, 47, 47, 0.22); background: rgba(140, 47, 47, 0.08); }
      .check--warning { border-color: rgba(140, 93, 27, 0.22); background: rgba(140, 93, 27, 0.08); }
      .check--success { border-color: rgba(29, 107, 95, 0.22); background: rgba(29, 107, 95, 0.08); }
      .check__title, .field__head { font-weight: 700; }
      .check__message, .field__desc, .field__auto { margin-top: 8px; }
      .field__env { margin-top: 6px; color: var(--accent); font-size: 12px; }
      .field__input { margin-top: 12px; }
      .field__desc, .field__auto { font-size: 13px; }
      .field__auto { color: var(--accent-2); }
      input, select { width: 100%; border: 1px solid rgba(44, 36, 29, 0.14); border-radius: 14px; padding: 12px 14px; font: inherit; color: var(--text); background: rgba(255, 252, 246, 0.92); }
      .secret-state { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; background: rgba(44, 36, 29, 0.08); color: var(--muted); font-size: 12px; font-weight: 600; }
      .secret-state--set { background: rgba(29, 107, 95, 0.12); color: var(--accent-2); }
      code { font-family: "IBM Plex Mono", Consolas, monospace; }
      @media (max-width: 760px) {
        .page { padding: 18px 12px 32px; }
        .hero, .card { border-radius: 20px; }
        .preset__top { flex-direction: column; }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <span class="hero__eyebrow">Config Center</span>
        <h1>AgentGraphRAG 配置中心</h1>
        <p>在这里配置回答模型、推理模型、Embedding、Milvus、Neo4j 和 MySQL。页面会把配置写入项目根目录的 <code>__ENV_FILE__</code>，并提供连通性测试。</p>
        <div class="nav">
          <a href="/workspace">工作台</a>
          <a class="alt" href="/settings">配置中心</a>
          <a class="alt" href="/api/v1/prompts" target="_blank" rel="noreferrer">Prompt Registry</a>
          <a class="alt" href="/health" target="_blank" rel="noreferrer">健康检查</a>
        </div>
        <div class="hero__meta">
          <span class="chip"><strong>统一前缀</strong> __ENV_PREFIX__*</span>
          <span class="chip"><strong>入口</strong> /settings</span>
          <span class="chip"><strong>API</strong> /api/v1/settings/*</span>
          <span class="chip"><strong>密钥策略</strong> 留空即保留旧值</span>
        </div>
        <div class="summary">
          <span class="chip"><strong>__ERRORS__</strong> 个错误</span>
          <span class="chip"><strong>__WARNINGS__</strong> 个警告</span>
          <span class="chip"><strong>__INFOS__</strong> 个提示</span>
          <span class="chip"><strong>__SUCCESS__</strong> 个就绪项</span>
        </div>
        __ALERT_HTML__
        <div class="actions">
          <button type="button" class="button alt" onclick="testConnections()">测试当前连接</button>
          <div id="testResult">等待执行连接测试。</div>
        </div>
      </section>
      <form method="post" action="/settings">
        <div class="stack">
          __PRESET_HTML__
          <section class="card">
            <div class="card__title">配置体检</div>
            <p class="card__intro">下面的结果基于当前已保存值和你选择的 provider/mode 计算。</p>
            <div class="check-grid">__CHECK_HTML__</div>
          </section>
          __SECTION_HTML__
        </div>
        <div class="actions">
          <div style="color:var(--muted);line-height:1.6;max-width:860px;">保存后会更新 <code>.env</code>。涉及已初始化的全局连接时，建议重启 <code>uvicorn</code> 再继续验证。</div>
          <button type="submit" class="save-button">保存配置</button>
        </div>
      </form>
    </main>
    <script>
      const presetCatalog = __PAGE_DATA__;
      function applyPreset(group, key) {
        const groupPresets = presetCatalog[group] || {};
        const preset = groupPresets[key];
        if (!preset) return;
        const groupInput = document.getElementById(group);
        if (groupInput) groupInput.value = key;
        const defaults = preset.defaults || {};
        Object.keys(defaults).forEach((fieldName) => {
          const input = document.getElementById(fieldName);
          if (!input) return;
          if (input.tagName === 'SELECT' || input.type !== 'password') input.value = defaults[fieldName];
        });
      }
      async function testConnections() {
        const box = document.getElementById('testResult');
        box.textContent = '正在测试 MySQL / Milvus / Neo4j ...';
        box.className = '';
        try {
          const response = await fetch('/api/v1/settings/test-connections');
          const data = await response.json();
          box.textContent = JSON.stringify(data, null, 2);
          box.className = data.summary && data.summary.ok ? '' : 'warn';
        } catch (error) {
          box.textContent = '连接测试失败：' + error.message;
          box.className = 'warn';
        }
      }
    </script>
  </body>
</html>
"""
    alert_html = f'<div class="alert">{escape(message)}</div>' if message else ""
    return (
        template.replace("__ENV_FILE__", escape(str(ENV_FILE)))
        .replace("__ENV_PREFIX__", escape(APP_ENV_PREFIX))
        .replace("__ERRORS__", str(summary["errors"]))
        .replace("__WARNINGS__", str(summary["warnings"]))
        .replace("__INFOS__", str(summary["infos"]))
        .replace("__SUCCESS__", str(summary["success"]))
        .replace("__ALERT_HTML__", alert_html)
        .replace("__PRESET_HTML__", "".join(preset_sections_html))
        .replace("__CHECK_HTML__", "".join(check_cards))
        .replace("__SECTION_HTML__", "".join(sections_html))
        .replace("__PAGE_DATA__", json.dumps(preset_payload, ensure_ascii=False))
    )
