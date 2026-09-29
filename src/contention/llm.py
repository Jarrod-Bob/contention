"""The one place LLM clients are built, enforcing which providers may receive YouTube data.

Only providers that don't train on inputs and keep them 30 days or less may receive
API Data (spec §2, decision #47):

- Anthropic, through LangChain for answers and the SDK for Message Batches. Each
  batch is deleted once its results are stored (`store_then_delete_batch`).
- OpenRouter, only with every request asking for zero-retention endpoints that don't
  collect data. A model with no such endpoint fails; it never falls through.
- Ollama, local only, with Ollama's cloud models off.

No hosted tracing: LangSmith is switched off whenever a client is built. Real Drafts
only go to Claude (ADR 0002).
"""

import json
import os
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlsplit

import anthropic
import httpx2
import langsmith
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

OPENROUTER_API = "https://openrouter.ai/api/v1"
OPENROUTER_PROVIDER = {"zdr": True, "data_collection": "deny"}
CLAUDE_EFFORT = "medium"
MAX_TOKENS = 16_000
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class ProviderNotAllowed(ValueError):
    """The model can't be used here: its provider may not receive this data."""


def chat_model(spec: str, *, real_draft: bool = False, transport: httpx2.MockTransport | None = None) -> BaseChatModel:
    """A LangChain chat model from `provider:model`, e.g. `anthropic:claude-opus-5-5`,
    `openrouter:qwen/qwen3.8-27b:free` or `ollama:qwen3:8b`.

    Pass `real_draft=True` when the prompt will carry a real (not sample) Draft: only
    Claude is allowed then. `transport` replaces OpenRouter's HTTP transport (sync and
    async), for tests.
    """
    provider, _, model = spec.partition(":")
    if real_draft and provider != "anthropic":
        raise ProviderNotAllowed(f"real Drafts only go to Claude, not {spec}")
    guard_environment()
    if provider == "anthropic":
        return ChatAnthropic(model=model, effort=CLAUDE_EFFORT, max_tokens=MAX_TOKENS)
    if provider == "openrouter":
        return _openrouter(model, transport)
    if provider == "ollama":
        return _ollama(model)
    raise ProviderNotAllowed(f"unknown provider in {spec!r}: use anthropic, openrouter or ollama")


def guard_environment() -> None:
    """Switch off hosted tracing and Ollama's cloud models for this process."""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    langsmith.configure(enabled=False)  # wins over any tracing environment variable
    os.environ["OLLAMA_NO_CLOUD"] = "1"


def _openrouter(model: str, transport: httpx2.MockTransport | None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_API,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        max_tokens=MAX_TOKENS,
        http_client=httpx2.Client(transport=_ZeroRetention(transport or httpx2.HTTPTransport())),
        http_async_client=httpx2.AsyncClient(transport=_AsyncZeroRetention(transport or httpx2.AsyncHTTPTransport())),
    )


def _with_provider_settings(request: httpx2.Request) -> httpx2.Request:
    """The request with OpenRouter's provider settings forced into its JSON body.

    Done on the wire, so no per-call argument (`extra_body` and the like) can drop them.
    """
    if request.method != "POST":
        return request
    body = json.loads(request.content)
    body["provider"] = {**body.get("provider", {}), **OPENROUTER_PROVIDER}
    headers = [(k, v) for k, v in request.headers.multi_items() if k.lower() != "content-length"]
    return httpx2.Request(
        request.method, request.url, headers=headers, content=json.dumps(body).encode(),
        extensions=request.extensions,
    )


class _ZeroRetention(httpx2.BaseTransport):
    def __init__(self, inner: httpx2.BaseTransport):
        self._inner = inner

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        return self._inner.handle_request(_with_provider_settings(request))

    def close(self) -> None:
        self._inner.close()


class _AsyncZeroRetention(httpx2.AsyncBaseTransport):
    def __init__(self, inner: httpx2.AsyncBaseTransport):
        self._inner = inner

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        return await self._inner.handle_async_request(_with_provider_settings(request))

    async def aclose(self) -> None:
        await self._inner.aclose()


def _ollama(model: str) -> ChatOllama:
    if model.endswith("cloud"):  # e.g. gpt-oss:120b-cloud runs on Ollama's servers
        raise ProviderNotAllowed(f"{model} is an Ollama cloud model; only local models may be used")
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    base_url = host if "://" in host else f"http://{host}"
    if urlsplit(base_url).hostname not in LOCAL_HOSTS:
        raise ProviderNotAllowed(f"Ollama must run locally, not at {host}")
    return ChatOllama(model=model, base_url=base_url)


def anthropic_client() -> anthropic.Anthropic:
    """The Anthropic SDK client, for Message Batches. Never use its Files API for API Data."""
    guard_environment()
    return anthropic.Anthropic()


def store_then_delete_batch(client: Any, batch_id: str, store: Callable[[Iterable], None]) -> None:
    """Hand an ended Message Batch's results to `store`, then delete the batch.

    Anthropic keeps batch results for 29 days otherwise. `store` must have saved the
    results (e.g. committed them to Postgres) when it returns; if it raises, the batch
    is kept so the results can be fetched again. `client` comes from `anthropic_client()`.
    """
    store(list(client.messages.batches.results(batch_id)))
    client.messages.batches.delete(batch_id)
