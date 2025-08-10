from types import SimpleNamespace
import importlib

import pytest


def _fake_openai_class_factory(embedding_length: int, raise_exc: Exception | None = None):
    """Builds a fake OpenAI class with embeddings.create() behavior you control."""
    class FakeEmbeddings:
        @staticmethod
        def create(model: str, input: str, dimensions: int):
            if raise_exc:
                raise raise_exc
            # Return an object that looks like the OpenAI SDK response
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.0] * embedding_length)]
            )

    class FakeOpenAI:
        def __init__(self, api_key: str | None = None):
            self.embeddings = FakeEmbeddings()

    return FakeOpenAI


@pytest.fixture
def svc(monkeypatch):
    # Import the service module fresh so monkeypatching hits its globals
    mod = importlib.import_module("app.services.embedding_service.cloud_embedding_service")

    # Ensure format_event returns a stable string without touching your DB/models
    monkeypatch.setattr(mod, "format_event", lambda event: "Title | Desc | Skopje | Tech | 2025-09-01 | Organizer", raising=True)

    # Fake OpenAI client that returns a 1024-d vector
    FakeOpenAI = _fake_openai_class_factory(embedding_length=1024)
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)

    # Ensure expected config
    monkeypatch.setattr(mod.Config, "OPENAI_API_KEY", "dummy")
    monkeypatch.setattr(mod.Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024)

    # Build service
    service = mod.CloudEmbeddingService()
    return service


def test_create_embedding_ok(svc):
    class DummyEvent:
        pass

    emb = svc.create_embedding(DummyEvent())
    assert isinstance(emb, list)
    assert len(emb) == 1024


def test_create_query_embedding_ok(svc):
    emb = svc.create_query_embedding("find events about ai in skopje")
    assert isinstance(emb, list)
    assert len(emb) == 1024


def test_openai_returns_no_data(monkeypatch):
    mod = importlib.import_module("app.services.embedding_service.cloud_embedding_service")
    monkeypatch.setattr(mod, "format_event", lambda e: "something", raising=True)

    # Fake client with empty data
    class FakeEmbeddings:
        @staticmethod
        def create(model: str, input: str, dimensions: int):
            return SimpleNamespace(data=[])

    class FakeOpenAI:
        def __init__(self, api_key=None):
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024)

    svc = mod.CloudEmbeddingService()

    class DummyEvent: pass
    with pytest.raises(RuntimeError, match="no embedding data"):
        svc.create_embedding(DummyEvent())


def test_mismatched_dimension_raises(monkeypatch):
    mod = importlib.import_module("app.services.embedding_service.cloud_embedding_service")
    monkeypatch.setattr(mod, "format_event", lambda e: "ok", raising=True)

    # Fake client that returns the wrong length (100)
    FakeOpenAI = _fake_openai_class_factory(embedding_length=100)
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024)

    svc = mod.CloudEmbeddingService()

    class DummyEvent: pass
    with pytest.raises(ValueError, match="Expected 1024-dim embedding"):
        svc.create_embedding(DummyEvent())


def test_empty_text_rejected(monkeypatch):
    mod = importlib.import_module("app.services.embedding_service.cloud_embedding_service")
    # Force empty/whitespace string from format_event
    monkeypatch.setattr(mod, "format_event", lambda e: "   ", raising=True)

    # Still need a fake OpenAI in ctor, but it won't be called
    FakeOpenAI = _fake_openai_class_factory(embedding_length=1024)
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024)

    svc = mod.CloudEmbeddingService()

    class DummyEvent: pass
    with pytest.raises(ValueError, match="Cannot embed empty text"):
        svc.create_embedding(DummyEvent())
