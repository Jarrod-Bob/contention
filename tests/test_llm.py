import asyncio
import json
import os

import httpx2
import langsmith
import openai
import pytest
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langsmith.utils import tracing_is_enabled

from contention.llm import ProviderNotAllowed, anthropic_client, chat_model, store_then_delete_batch
from fake_anthropic import FakeAnthropic

ZDR = {"zdr": True, "data_collection": "deny"}


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    """Keys for every provider, and the guarded settings put back after each test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter")
    for name in ("OLLAMA_NO_CLOUD", "OLLAMA_HOST", "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.delenv(name, raising=False)
    yield
    langsmith.configure(enabled=None)


def fake_openrouter(status=200):
    """An httpx2 transport answering every chat completion, keeping the request bodies it saw."""
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        if status != 200:
            return httpx2.Response(status, json={"error": {"message": "No endpoints found matching your data policy"}})
        return httpx2.Response(200, json={
            "id": "gen-1", "object": "chat.completion", "created": 0, "model": "qwen/qwen3.8-27b:free",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
        })

    return httpx2.MockTransport(handler), bodies


def test_openrouter_requests_ask_for_zero_retention_and_no_data_collection():
    transport, bodies = fake_openrouter()
    model = chat_model("openrouter:qwen/qwen3.8-27b:free", transport=transport)

    model.invoke("Which Videos did well?")
    model.invoke("And which did not?")

    assert len(bodies) == 2
    assert all(body["provider"] == ZDR for body in bodies)
    assert bodies[0]["model"] == "qwen/qwen3.8-27b:free"


def test_async_openrouter_requests_carry_the_same_settings():
    transport, bodies = fake_openrouter()
    model = chat_model("openrouter:qwen/qwen3.8-27b:free", transport=transport)

    asyncio.run(model.ainvoke("Which Videos did well?"))

    assert bodies[0]["provider"] == ZDR


def test_openrouter_settings_cannot_be_overridden_per_call():
    transport, bodies = fake_openrouter()
    model = chat_model("openrouter:qwen/qwen3.8-27b:free", transport=transport)

    model.invoke("hi", extra_body={"provider": {"zdr": False, "data_collection": "allow", "sort": "price"}})

    assert bodies[0]["provider"] == {**ZDR, "sort": "price"}


def test_openrouter_request_with_no_eligible_endpoint_fails():
    transport, bodies = fake_openrouter(status=404)
    model = chat_model("openrouter:qwen/qwen3.8-27b:free", transport=transport)

    with pytest.raises(openai.NotFoundError):
        model.invoke("hi")
    assert [body["model"] for body in bodies] == ["qwen/qwen3.8-27b:free"]  # no other model tried


def test_claude_is_opus_with_explicit_effort():
    model = chat_model("anthropic:claude-opus-5-5")

    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-opus-5-5"
    assert model.reasoning_effort == "medium"


def test_ollama_runs_local_with_cloud_models_off():
    model = chat_model("ollama:qwen3:8b")

    assert isinstance(model, ChatOllama)
    assert os.environ["OLLAMA_NO_CLOUD"] == "1"


@pytest.mark.parametrize("spec", ["ollama:gpt-oss:120b-cloud", "ollama:qwen3-coder:480b-cloud"])
def test_ollama_cloud_models_are_refused(spec):
    with pytest.raises(ProviderNotAllowed):
        chat_model(spec)


def test_ollama_on_a_remote_host_is_refused(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "https://ollama.com")

    with pytest.raises(ProviderNotAllowed):
        chat_model("ollama:qwen3:8b")


def test_unknown_provider_is_refused():
    with pytest.raises(ProviderNotAllowed):
        chat_model("openai:gpt-5")


@pytest.mark.parametrize("spec", ["anthropic:claude-opus-5-5", "openrouter:qwen/qwen3.8-27b:free", "ollama:qwen3:8b"])
def test_hosted_tracing_is_off_even_when_the_environment_turns_it_on(monkeypatch, spec):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    chat_model(spec)

    assert tracing_is_enabled() is False
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_a_real_draft_can_go_to_claude():
    model = chat_model("anthropic:claude-opus-5-5", real_draft=True)

    assert isinstance(model, ChatAnthropic)


@pytest.mark.parametrize("spec", ["openrouter:qwen/qwen3.8-27b:free", "ollama:qwen3:8b"])
def test_a_real_draft_cannot_reach_a_non_claude_model(spec):
    transport, bodies = fake_openrouter()

    with pytest.raises(ProviderNotAllowed):
        chat_model(spec, real_draft=True, transport=transport)
    assert bodies == []


def test_anthropic_client_is_built_with_tracing_off(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")

    anthropic_client()

    assert tracing_is_enabled() is False


def test_batch_is_deleted_once_its_results_are_stored():
    client = FakeAnthropic({"batch-1": ["result a", "result b"]})
    stored = []

    def store(results):
        assert client.messages.batches.calls == [("results", "batch-1")]  # not deleted yet
        stored.extend(results)

    store_then_delete_batch(client, "batch-1", store)

    assert stored == ["result a", "result b"]
    assert client.messages.batches.calls == [("results", "batch-1"), ("delete", "batch-1")]


def test_batch_is_kept_when_storing_fails():
    client = FakeAnthropic({"batch-1": ["result a"]})

    def store(results):
        raise RuntimeError("database down")

    with pytest.raises(RuntimeError):
        store_then_delete_batch(client, "batch-1", store)
    assert ("delete", "batch-1") not in client.messages.batches.calls
