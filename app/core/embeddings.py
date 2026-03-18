from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from typing import Any

import httpx

from app.core.config import Settings, get_settings


DEFAULT_DASHSCOPE_EMBEDDING_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
DEFAULT_EMBEDDING_TIMEOUT = 30.0
DEFAULT_BATCH_SIZE = 8
OPENAI_COMPATIBLE_EMBEDDING_PROVIDERS = {"openai", "azure-openai", "openai-compatible", "ollama"}


class EmbeddingProviderError(RuntimeError):
    pass


def _normalize(vector: Iterable[float]) -> list[float]:
    values = [float(item) for item in vector]
    norm = math.sqrt(sum(item * item for item in values)) or 1.0
    return [item / norm for item in values]


def _chunked(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _local_embed(text: str, dimensions: int) -> list[float]:
    size = max(8, dimensions)
    buckets = [0.0] * size
    raw = text.encode("utf-8")
    if not raw:
        return buckets
    digest = hashlib.sha256(raw).digest()
    for index, value in enumerate(raw):
        bucket = (value + digest[index % len(digest)] + index * 31) % size
        buckets[bucket] += 0.35 + (value / 255.0)
    return _normalize(buckets)


class LocalEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [_local_embed(text, self.settings.embedding_dimensions) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return _local_embed(text, self.settings.embedding_dimensions)


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _endpoint(self) -> str:
        base_url = self.settings.embedding_base_url.strip()
        if not base_url:
            raise EmbeddingProviderError("embedding_base_url is required for OpenAI-compatible embeddings")
        if base_url.endswith("/embeddings"):
            return base_url
        return f"{base_url.rstrip('/')}/embeddings"

    def _headers(self) -> dict[str, str]:
        if not self.settings.embedding_api_key and self.settings.embedding_provider != "ollama":
            raise EmbeddingProviderError("embedding_api_key is required for this embedding provider")
        headers = {"Content-Type": "application/json"}
        if self.settings.embedding_provider == "azure-openai":
            headers["api-key"] = self.settings.embedding_api_key
        elif self.settings.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.settings.embedding_api_key}"
        return headers

    def _post(self, inputs: Sequence[str]) -> list[list[float]]:
        payload: dict[str, Any] = {"model": self.settings.embedding_model, "input": list(inputs)}
        with httpx.Client(timeout=DEFAULT_EMBEDDING_TIMEOUT) as client:
            response = client.post(self._endpoint(), headers=self._headers(), json=payload)
        if response.status_code >= 400:
            raise EmbeddingProviderError(f"Embedding request failed with status {response.status_code}: {response.text}")
        data = response.json()
        embeddings = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        if len(embeddings) != len(inputs):
            raise EmbeddingProviderError("Embedding response size does not match request size")
        return [_normalize(item.get("embedding", [])) for item in embeddings]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for batch in _chunked(texts, DEFAULT_BATCH_SIZE):
            vectors.extend(self._post(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._post([text])[0]


class DashScopeEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _endpoint(self) -> str:
        return self.settings.embedding_base_url.strip() or DEFAULT_DASHSCOPE_EMBEDDING_URL

    def _headers(self) -> dict[str, str]:
        if not self.settings.embedding_api_key:
            raise EmbeddingProviderError("embedding_api_key is required for DashScope embeddings")
        return {
            "Authorization": f"Bearer {self.settings.embedding_api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, inputs: Sequence[str], *, text_type: str, instruct: str | None = None) -> list[list[float]]:
        payload = {
            "model": self.settings.embedding_model,
            "input": {"texts": list(inputs)},
            "parameters": {
                "text_type": text_type,
                "dimension": self.settings.embedding_dimensions,
                **({"instruct": instruct} if instruct and text_type == "query" else {}),
            },
        }
        with httpx.Client(timeout=DEFAULT_EMBEDDING_TIMEOUT) as client:
            response = client.post(self._endpoint(), headers=self._headers(), json=payload)
        if response.status_code >= 400:
            raise EmbeddingProviderError(f"DashScope embedding request failed with status {response.status_code}: {response.text}")
        data = response.json()
        embeddings = sorted(data.get("output", {}).get("embeddings", []), key=lambda item: item.get("text_index", 0))
        if len(embeddings) != len(inputs):
            raise EmbeddingProviderError("DashScope embedding response size does not match request size")
        return [_normalize(item.get("embedding", [])) for item in embeddings]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for batch in _chunked(texts, DEFAULT_BATCH_SIZE):
            vectors.extend(self._post(batch, text_type="document"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        instruction = self.settings.embedding_query_instruction.strip() or None
        return self._post([text], text_type="query", instruct=instruction)[0]


def build_embedding_provider(settings: Settings | None = None) -> LocalEmbeddingProvider | OpenAICompatibleEmbeddingProvider | DashScopeEmbeddingProvider:
    settings = settings or get_settings()
    provider = settings.embedding_provider.strip().lower()
    if provider == "dashscope":
        return DashScopeEmbeddingProvider(settings)
    if provider in OPENAI_COMPATIBLE_EMBEDDING_PROVIDERS and settings.embedding_base_url.strip():
        return OpenAICompatibleEmbeddingProvider(settings)
    if provider in {"local", "ollama"}:
        return LocalEmbeddingProvider(settings)
    if provider in OPENAI_COMPATIBLE_EMBEDDING_PROVIDERS:
        return OpenAICompatibleEmbeddingProvider(settings)
    raise EmbeddingProviderError(f"Unsupported embedding provider: {settings.embedding_provider}")


def embed_documents(texts: Sequence[str], settings: Settings | None = None) -> list[list[float]]:
    return build_embedding_provider(settings).embed_documents(texts)


def embed_query(text: str, settings: Settings | None = None) -> list[float]:
    return build_embedding_provider(settings).embed_query(text)
