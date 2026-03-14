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
    if field_name in SECRET_FIELD_NAMES:
        return "******" if value else ""
    return value


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
        return (
            f'<input type="{field.input_type}" name="{field_name}" id="{field_name}" '
            f'placeholder="{escape(placeholder, quote=True)}" value="" autocomplete="off" />'
        )

    return (
        f'<input type="{field.input_type}" name="{field_name}" id="{field_name}" '
        f'placeholder="{escape(field.placeholder, quote=True)}" value="{escape(value, quote=True)}" />'
    )


def render_settings_page(message: str | None = None) -> str:
    raw_values = current_settings_values()
    resolved_values = resolve_settings_values(raw_values)
    checks = build_config_checks(raw_values)
    summary = _build_summary(checks)
    preset_payload = {
        group: {preset.key: {"defaults": preset.defaults, "key": preset.key} for preset in presets}
        for group, presets in PRESET_GROUPS.items()
    }

    alert_html = f'<div class="alert">{escape(message)}</div>' if message else ""

    preset_sections_html: list[str] = []
    for group in PRESET_GROUP_ORDER:
        title, intro = PRESET_GROUP_META[group]
        preset_cards: list[str] = []
        for preset in PRESET_GROUPS[group]:
            notes_html = "".join(f"<li>{escape(note)}</li>" for note in preset.notes)
            docs_html = ""
            if preset.docs_url:
                docs_html = f'<a class="preset__link" href="{escape(preset.docs_url, quote=True)}" target="_blank" rel="noreferrer">{escape(preset.docs_label)}</a>'
            preset_cards.append(
                f"""
                <article class="preset">
                  <div class="preset__top">
                    <div>
                      <h3>{escape(preset.label)}</h3>
                      <p>{escape(preset.summary)}</p>
                    </div>
                    <button type="button" class="preset__button" onclick="applyPreset('{escape(group, quote=True)}', '{escape(preset.key, quote=True)}')">应用预设</button>
                  </div>
                  {docs_html}
                  <ul class="preset__notes">{notes_html}</ul>
                </article>
                """
            )
        preset_sections_html.append(
            f"""
            <section class="card">
              <div class="card__title">{escape(title)}</div>
              <p class="card__intro">{escape(intro)}</p>
              <div class="preset-grid">{''.join(preset_cards)}</div>
            </section>
            """
        )

    check_cards: list[str] = []
    for check in checks:
        field_line = f'<div class="check__fields">{escape(check["field_labels"])}</div>' if check["field_labels"] else ""
        check_cards.append(
            f"""
            <article class="check check--{escape(check['level'], quote=True)}">
              <div class="check__title">{escape(check['title'])}</div>
              <div class="check__message">{escape(check['message'])}</div>
              {field_line}
            </article>
            """
        )
    checks_html = "".join(check_cards)

    sections_html: list[str] = []
    for section in SECTION_ORDER:
        title, intro = SECTION_META[section]
        fields_html: list[str] = []
        for field in CONFIG_FIELDS:
            if field.section != section:
                continue
            raw_value = raw_values[field.name]
            resolved_value = resolved_values[field.name]
            auto_fill_hint = ""
            if not raw_value and resolved_value and resolved_value != raw_value and not field.secret:
                auto_fill_hint = f'<div class="field__auto">保存时会按官方方案自动补全为：{escape(resolved_value)}</div>'
            secret_state = ""
            if field.secret:
                secret_state = (
                    '<span class="secret-state secret-state--set">已保存</span>' if raw_value else '<span class="secret-state">未设置</span>'
                )
            fields_html.append(
                f"""
                <label class="field" for="{field.name}">
                  <div class="field__head">
                    <span>{escape(field.label)}</span>
                    {secret_state}
                  </div>
                  <div class="field__env">{escape(env_var_name(field.name))}</div>
                  <div class="field__input">{_render_input(field.name, raw_value, field)}</div>
                  <div class="field__desc">{escape(field.description)}</div>
                  {auto_fill_hint}
                </label>
                """
            )
        sections_html.append(
            f"""
            <section class="card">
              <div class="card__title">{escape(title)}</div>
              <p class="card__intro">{escape(intro)}</p>
              <div class="grid">{''.join(fields_html)}</div>
            </section>
            """
        )

    page_data = json.dumps(preset_payload, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AgentGraphRAG 配置中心</title>
    <style>
      :root {{
        --bg: #f4efe7;
        --bg-accent: #e9e1d5;
        --panel: rgba(255, 251, 244, 0.94);
        --line: rgba(60, 46, 34, 0.14);
        --text: #2c241d;
        --muted: #6e5d50;
        --accent: #a5512a;
        --accent-2: #1d6b5f;
        --shadow: 0 22px 70px rgba(82, 54, 25, 0.12);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "IBM Plex Sans", "Noto Sans SC", sans-serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, rgba(165, 81, 42, 0.16), transparent 26%),
          radial-gradient(circle at bottom right, rgba(29, 107, 95, 0.16), transparent 28%),
          linear-gradient(135deg, var(--bg), var(--bg-accent));
      }}
      .page {{ max-width: 1240px; margin: 0 auto; padding: 28px 18px 48px; }}
      .hero, .card {{ border: 1px solid var(--line); border-radius: 26px; background: var(--panel); box-shadow: var(--shadow); }}
      .hero {{ padding: 28px; background: linear-gradient(135deg, rgba(255, 247, 237, 0.98), rgba(244, 236, 221, 0.94)); }}
      .hero__eyebrow {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: rgba(165, 81, 42, 0.12); color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
      h1 {{ margin: 16px 0 10px; font-size: clamp(32px, 4vw, 54px); line-height: 1.02; }}
      .hero p {{ margin: 0; max-width: 860px; color: var(--muted); line-height: 1.65; }}
      .hero__meta, .summary {{ display: flex; flex-wrap: wrap; gap: 10px; }}
      .hero__meta {{ margin-top: 18px; }}
      .summary {{ margin-top: 18px; }}
      .chip {{ padding: 9px 12px; border-radius: 999px; background: rgba(44, 36, 29, 0.07); color: var(--muted); font-size: 13px; }}
      .chip strong {{ color: var(--text); }}
      .alert {{ margin-top: 18px; padding: 14px 16px; border-radius: 18px; border: 1px solid rgba(29, 107, 95, 0.22); background: rgba(29, 107, 95, 0.11); color: var(--accent-2); font-weight: 600; }}
      form {{ margin-top: 20px; }}
      .stack {{ display: grid; gap: 18px; margin-top: 18px; }}
      .card {{ padding: 22px; }}
      .card__title {{ font-size: 22px; font-weight: 700; }}
      .card__intro {{ margin: 8px 0 0; color: var(--muted); line-height: 1.6; }}
      .preset-grid, .grid, .check-grid {{ display: grid; gap: 14px; margin-top: 18px; }}
      .preset-grid, .grid {{ grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
      .check-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
      .preset {{ display: grid; gap: 12px; padding: 16px; border-radius: 20px; border: 1px solid rgba(44, 36, 29, 0.08); background: rgba(255, 255, 255, 0.72); }}
      .preset__top {{ display: flex; gap: 12px; justify-content: space-between; align-items: flex-start; }}
      .preset h3 {{ margin: 0; font-size: 18px; }}
      .preset p {{ margin: 6px 0 0; color: var(--muted); line-height: 1.55; }}
      .preset__button, .save-button {{ border: 0; border-radius: 999px; padding: 12px 18px; font: inherit; font-weight: 700; color: white; background: linear-gradient(135deg, #c96f34, #8c4021); cursor: pointer; box-shadow: 0 14px 26px rgba(140, 64, 33, 0.16); }}
      .preset__link {{ color: var(--accent-2); font-weight: 600; text-decoration: none; }}
      .preset__notes {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.55; }}
      .check {{ padding: 16px; border-radius: 18px; border: 1px solid rgba(44, 36, 29, 0.08); background: rgba(255, 255, 255, 0.75); }}
      .check--error {{ border-color: rgba(140, 47, 47, 0.22); background: rgba(140, 47, 47, 0.08); }}
      .check--warning {{ border-color: rgba(140, 93, 27, 0.22); background: rgba(140, 93, 27, 0.08); }}
      .check--success {{ border-color: rgba(29, 107, 95, 0.22); background: rgba(29, 107, 95, 0.08); }}
      .check__title {{ font-weight: 700; }}
      .check__message {{ margin-top: 6px; line-height: 1.55; color: var(--muted); }}
      .check__fields {{ margin-top: 8px; font-size: 13px; color: var(--text); }}
      .field {{ display: block; padding: 16px; border-radius: 20px; border: 1px solid rgba(44, 36, 29, 0.08); background: rgba(255, 255, 255, 0.76); }}
      .field__head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; font-weight: 700; }}
      .field__env {{ margin-top: 6px; color: var(--accent); font-size: 12px; letter-spacing: 0.04em; }}
      .field__input {{ margin-top: 12px; }}
      .field__desc {{ margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.5; }}
      .field__auto {{ margin-top: 10px; color: var(--accent-2); font-size: 13px; line-height: 1.5; }}
      input, select {{ width: 100%; border: 1px solid rgba(44, 36, 29, 0.14); border-radius: 14px; padding: 12px 14px; font: inherit; color: var(--text); background: rgba(255, 252, 246, 0.92); }}
      input:focus, select:focus {{ outline: none; border-color: rgba(165, 81, 42, 0.5); box-shadow: 0 0 0 4px rgba(165, 81, 42, 0.12); }}
      .secret-state {{ display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; background: rgba(44, 36, 29, 0.08); color: var(--muted); font-size: 12px; font-weight: 600; }}
      .secret-state--set {{ background: rgba(29, 107, 95, 0.12); color: var(--accent-2); }}
      .actions {{ display: flex; justify-content: space-between; gap: 16px; margin-top: 18px; align-items: center; flex-wrap: wrap; }}
      .actions__note {{ color: var(--muted); line-height: 1.6; max-width: 860px; }}
      code {{ font-family: "IBM Plex Mono", "Consolas", monospace; }}
      @media (max-width: 760px) {{
        .page {{ padding: 18px 12px 32px; }}
        .hero, .card {{ border-radius: 20px; }}
        .preset__top {{ flex-direction: column; }}
        .preset__button, .save-button {{ width: 100%; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <span class="hero__eyebrow">Config Center</span>
        <h1>AgentGraphRAG 真实接入配置中心</h1>
        <p>
          这个页面不只是收纳环境变量，而是把 OpenAI、Azure OpenAI、DeepSeek、DashScope、Neo4j Aura、Milvus / Zilliz、Dify 等官方接入方案整理成统一配置模型，并写回项目根目录的 <code>{escape(str(ENV_FILE))}</code>。开发和生产环境会按这里的值连接真实 MySQL、Milvus 与 Neo4j，只有测试环境才保留本地 mock 分支。
        </p>
        <div class="hero__meta">
          <span class="chip"><strong>统一前缀</strong> {escape(APP_ENV_PREFIX)}*</span>
          <span class="chip"><strong>页面入口</strong> / 和 /settings</span>
          <span class="chip"><strong>API</strong> /api/v1/settings/schema 与 /api/v1/settings/state</span>
          <span class="chip"><strong>密钥策略</strong> 留空即保留旧值</span>
        </div>
        <div class="summary">
          <span class="chip"><strong>{summary['errors']}</strong> 个错误</span>
          <span class="chip"><strong>{summary['warnings']}</strong> 个警告</span>
          <span class="chip"><strong>{summary['infos']}</strong> 个提示</span>
          <span class="chip"><strong>{summary['success']}</strong> 个就绪项</span>
        </div>
        {alert_html}
      </section>
      <form method="post" action="/settings">
        <div class="stack">
          {''.join(preset_sections_html)}
          <section class="card">
            <div class="card__title">配置体检</div>
            <p class="card__intro">下面的结果基于当前已保存值和你选择的 provider/mode 计算，规则按官方方案整理，不再只是字段存在性检查。</p>
            <div class="check-grid">{checks_html}</div>
          </section>
          {''.join(sections_html)}
        </div>
        <div class="actions">
          <div class="actions__note">
            保存后会更新 <code>.env</code>。像 <code>app_name</code>、已初始化的全局连接、以及当前 import 时就创建的本地 store，仍建议重启 <code>uvicorn</code> 后再继续验证。页面会把安全可推断的官方默认值自动补进 env，例如 OpenAI 和 DeepSeek 的基础 URL。
          </div>
          <button type="submit" class="save-button">保存配置</button>
        </div>
      </form>
    </main>
    <script>
      const presetCatalog = {page_data};
      function applyPreset(group, key) {{
        const groupPresets = presetCatalog[group] || {{}};
        const preset = groupPresets[key];
        if (!preset) {{ return; }}
        const groupInput = document.getElementById(group);
        if (groupInput) {{ groupInput.value = key; }}
        const defaults = preset.defaults || {{}};
        Object.keys(defaults).forEach((fieldName) => {{
          const input = document.getElementById(fieldName);
          if (!input) {{ return; }}
          if (input.tagName === 'SELECT' || input.type !== 'password') {{ input.value = defaults[fieldName]; }}
        }});
      }}
    </script>
  </body>
</html>
"""
