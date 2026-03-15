from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import Settings, get_settings


DEFAULT_COMPLETIONS_TIMEOUT = 60.0


class LLMProviderError(RuntimeError):
    pass


ModelRole = Literal["answer", "reasoning"]


@dataclass(frozen=True)
class LLMProfile:
    role: ModelRole
    provider: str
    model: str
    base_url: str
    api_key: str
    api_version: str
    temperature: float
    max_tokens: int
    timeout_seconds: int


@dataclass(frozen=True)
class PromptPackage:
    system: str
    user: str


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    prompt_length: int
    used_fallback: bool = False


class LocalRuleBasedLLM:
    def __init__(self, profile: LLMProfile):
        self.profile = profile

    def complete(self, prompt: PromptPackage) -> LLMResult:
        combined = f"{prompt.system}\n\n{prompt.user}".strip()
        return LLMResult(
            content="",
            provider="rule-based",
            model=self.profile.model or "disabled",
            prompt_length=len(combined),
            used_fallback=True,
        )


class OpenAICompatibleLLM:
    def __init__(self, profile: LLMProfile):
        self.profile = profile

    def _endpoint(self) -> str:
        base_url = self.profile.base_url.strip()
        if not base_url:
            raise LLMProviderError(f"Missing base URL for {self.profile.role} model")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        provider = self.profile.provider
        headers = {"Content-Type": "application/json"}
        api_key = self.profile.api_key.strip()
        if provider == "azure-openai":
            if api_key:
                headers["api-key"] = api_key
        else:
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _payload(self, prompt: PromptPackage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.profile.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "temperature": self.profile.temperature,
            "max_tokens": self.profile.max_tokens,
        }
        if self.profile.provider == "azure-openai" and self.profile.api_version:
            payload["api-version"] = self.profile.api_version
        return payload

    def complete(self, prompt: PromptPackage) -> LLMResult:
        if not self.profile.model.strip():
            raise LLMProviderError(f"Missing model name for {self.profile.role} model")

        with httpx.Client(timeout=float(self.profile.timeout_seconds or DEFAULT_COMPLETIONS_TIMEOUT)) as client:
            response = client.post(self._endpoint(), headers=self._headers(), json=self._payload(prompt))
        if response.status_code >= 400:
            raise LLMProviderError(f"LLM request failed with status {response.status_code}: {response.text}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError("LLM response does not contain choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            content = "\n".join(part for part in text_parts if part)
        return LLMResult(
            content=content,
            provider=self.profile.provider,
            model=self.profile.model,
            prompt_length=len(prompt.system) + len(prompt.user),
            used_fallback=False,
        )


SUPPORTED_CHAT_PROVIDERS = {"openai", "azure-openai", "deepseek", "dashscope", "openai-compatible", "ollama"}


def _resolve_role_profile(settings: Settings, role: ModelRole) -> LLMProfile:
    provider = settings.llm_provider.strip().lower()
    if role == "answer":
        return LLMProfile(
            role=role,
            provider=provider,
            model=settings.answer_llm_model,
            base_url=settings.answer_llm_base_url or settings.llm_base_url,
            api_key=settings.answer_llm_api_key or settings.llm_api_key,
            api_version=settings.answer_llm_api_version or settings.llm_api_version,
            temperature=settings.answer_llm_temperature,
            max_tokens=settings.answer_llm_max_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return LLMProfile(
        role=role,
        provider=provider,
        model=settings.reasoning_llm_model,
        base_url=settings.reasoning_llm_base_url or settings.llm_base_url,
        api_key=settings.reasoning_llm_api_key or settings.llm_api_key,
        api_version=settings.reasoning_llm_api_version or settings.llm_api_version,
        temperature=settings.reasoning_llm_temperature,
        max_tokens=settings.reasoning_llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def build_llm_client(role: ModelRole, settings: Settings | None = None) -> LocalRuleBasedLLM | OpenAICompatibleLLM:
    settings = settings or get_settings()
    profile = _resolve_role_profile(settings, role)
    if not profile.provider:
        return LocalRuleBasedLLM(profile)
    if profile.provider not in SUPPORTED_CHAT_PROVIDERS:
        raise LLMProviderError(f"Unsupported LLM provider: {profile.provider}")
    return OpenAICompatibleLLM(profile)


def complete_prompt(role: ModelRole, prompt: PromptPackage, settings: Settings | None = None) -> LLMResult:
    client = build_llm_client(role, settings)
    try:
        return client.complete(prompt)
    except LLMProviderError:
        if isinstance(client, LocalRuleBasedLLM):
            raise
        fallback_profile = _resolve_role_profile(settings or get_settings(), role)
        return LocalRuleBasedLLM(fallback_profile).complete(prompt)


def try_parse_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
