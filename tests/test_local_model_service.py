from unittest.mock import MagicMock
import pytest

from app.services.model.local_model_service_impl import LocalModelService
from app.configuration import config as config_module

class DummyEvent:
    def __init__(self, title):
        self.title = title

@pytest.fixture(autouse=True)
def set_config(monkeypatch):
    # ensure Config has what the service expects
    monkeypatch.setattr(config_module.Config, "OLLAMA_URL", "http://fake-ollama:11434", raising=False)
    monkeypatch.setattr(config_module.Config, "OLLAMA_LLM", "llama3.1:8b", raising=False)
    monkeypatch.setattr(config_module.Config, "LLM_OPTIONS", {"temperature": 0}, raising=False)
    monkeypatch.setattr(config_module.Config, "RAG_TOP_K", 3, raising=False)

@pytest.fixture
def repo_mock():
    repo = MagicMock(spec=["search_by_embedding"])
    return repo

@pytest.fixture
def embed_mock():
    svc = MagicMock(spec=["create_embedding"])
    svc.create_embedding.return_value = [0.01, 0.02, 0.03]
    return svc

@pytest.fixture
def fake_client(monkeypatch):
    class FakeClient:
        def __init__(self, host: str):
            self.host = host
            self.last_call = None
        def chat(self, model, messages, options=None):
            # store inputs so tests can assert on them
            self.last_call = {"model": model, "messages": messages, "options": options}
            return {"message": {"content": "Hello from fake LLM"}}
    monkeypatch.setattr("app.services.model.local_model_service_impl.Client", FakeClient)
    return FakeClient

def test_query_prompt_happy_path(repo_mock, embed_mock, fake_client, monkeypatch):
    # Return some fake events from the repository
    repo_mock.search_by_embedding.return_value = [DummyEvent("A"), DummyEvent("B")]

    # Make format_event stable
    def fake_format_event(ev): return f"Event: {ev.title}"
    monkeypatch.setattr("app.services.model.local_model_service_impl.format_event", fake_format_event)

    # Build service; make sure it has sys_prompt (your base class must set this!)
    svc = LocalModelService(event_repository=repo_mock, embedding_service=embed_mock)
    # If your base ModelService doesn’t set sys_prompt, set it here:
    if not hasattr(svc, "sys_prompt"):
        svc.sys_prompt = "You are a helpful event assistant."

    out = svc.query_prompt("what should I do tonight?")
    assert out == "Hello from fake LLM"

    # Verify repository was used with the embedded vector and top_k
    repo_mock.search_by_embedding.assert_called_once()
    args, kwargs = repo_mock.search_by_embedding.call_args
    assert args[0] == [0.01, 0.02, 0.03]
    assert args[1] == 3  # RAG_TOP_K

def test_build_messages_structure(repo_mock, embed_mock):
    svc = LocalModelService(event_repository=repo_mock, embedding_service=embed_mock)
    svc.sys_prompt = "SYS"
    msgs = svc.build_messages("SYS", "ctx-line-1\nctx-line-2", "USER PROMPT")
    assert msgs[0]["role"] == "system"
    assert "SYS" in msgs[0]["content"]
    assert "ctx-line-1" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "USER PROMPT"

def test_get_rag_context_empty(repo_mock, embed_mock, monkeypatch):
    # No events returned
    repo_mock.search_by_embedding.return_value = []

    # format_event won’t be called, but we can still stub it
    monkeypatch.setattr("app.services.model.local_model_service_impl.format_event", lambda e: "SHOULD_NOT_APPEAR")

    svc = LocalModelService(event_repository=repo_mock, embedding_service=embed_mock)
    ctx = svc.get_rag_data_and_create_context("hello")
    assert ctx == ""




