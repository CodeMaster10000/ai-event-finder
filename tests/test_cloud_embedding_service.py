from types import SimpleNamespace
import importlib
import pytest


def _fake_openai_class_factory(embedding_length: int, raise_exc: Exception | None = None):
    """Build a fake OpenAI class with embeddings.create() behavior you control."""
    class FakeEmbeddings:
        @staticmethod
        def create(model: str, input: str, dimensions: int):
            if raise_exc:
                raise raise_exc
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.0] * embedding_length)]
            )

    class FakeOpenAI:
        def __init__(self, api_key: str | None = None):
            self.embeddings = FakeEmbeddings()

    return FakeOpenAI


@pytest.fixture
def mod():
    # Import the module under test
    return importlib.import_module("app.services.embedding_service.cloud_embedding_service")


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """
    Set sane defaults ONCE for every test:
    - Config.* values
    - A default OpenAI fake returning a 1024-d embedding
    If a test needs different OpenAI behavior, it can override with monkeypatch again.
    """
    monkeypatch.setenv("EMBEDDING_PROVIDER", "cloud")
    mod = importlib.import_module("app.services.embedding_service.cloud_embedding_service")
    monkeypatch.setattr(mod.Config, "OPENAI_API_KEY", "dummy", raising=True)
    monkeypatch.setattr(mod.Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large", raising=True)
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024, raising=True)

    FakeOpenAI = _fake_openai_class_factory(embedding_length=1024)
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)


@pytest.fixture
def svc(mod):
    # With defaults applied, build a fresh service
    return mod.CloudEmbeddingService()


def test_create_embedding_ok(svc):
    emb = svc.create_embedding("Title | Desc | Skopje | Tech | 2025-09-01 | Organizer")
    assert isinstance(emb, list)
    assert len(emb) == 1024


def test_provider_exception_wrapped(monkeypatch, mod):
    # Override default OpenAI to raise
    FakeOpenAI = _fake_openai_class_factory(embedding_length=0, raise_exc=Exception("boom"))
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)

    svc = mod.CloudEmbeddingService()
    with pytest.raises(mod.EmbeddingServiceException, match="OpenAI embedding request failed"):
        svc.create_embedding("some text")


def test_unexpected_payload_wrapped(monkeypatch, mod):
    # Override to return empty data -> triggers our "unexpected payload" path
    class FakeEmbeddings:
        @staticmethod
        def create(model: str, input: str, dimensions: int):
            return SimpleNamespace(data=[])

    class FakeOpenAI:
        def __init__(self, api_key=None):
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)

    svc = mod.CloudEmbeddingService()
    with pytest.raises(mod.EmbeddingServiceException, match="unexpected embedding payload"):
        svc.create_embedding("whatever")


def test_mismatched_dimension_raises(monkeypatch, mod):
    # Override to wrong length (100)
    FakeOpenAI = _fake_openai_class_factory(embedding_length=100)
    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI, raising=True)

    svc = mod.CloudEmbeddingService()
    with pytest.raises(mod.EmbeddingServiceException, match=r"Expected 1024-dim embedding, got 100"):
        svc.create_embedding("ok")


def test_empty_text_rejected(svc, mod):
    with pytest.raises(mod.EmbeddingServiceException, match="non-empty string"):
        svc.create_embedding("   ")