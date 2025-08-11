from types import SimpleNamespace
import importlib
import pytest


class _FakeEmbeddingsOK:
    """Returns a data payload with a vector of the requested length."""
    def __init__(self, length=1024):
        self.length = length

    def create(self, model: str, input: str, dimensions: int):
        # mimic the OpenAI SDK response shape
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.0] * self.length)])


class _FakeEmbeddingsRaise:
    """Raises a provided exception when create() is called."""
    def __init__(self, exc: Exception):
        self.exc = exc

    def create(self, model: str, input: str, dimensions: int):
        raise self.exc


class _FakeEmbeddingsEmpty:
    """Returns an empty data list to simulate unexpected payload."""
    @staticmethod
    def create(model: str, input: str, dimensions: int):
        return SimpleNamespace(data=[])


class _FakeOpenAI:
    """Container for the embeddings subclient, like the real OpenAI client."""
    def __init__(self, embeddings):
        self.embeddings = embeddings


@pytest.fixture
def mod():
    # Import the module under test
    return importlib.import_module("app.services.embedding_service.cloud_embedding_service")


@pytest.fixture(autouse=True)
def _defaults(monkeypatch, mod):
    """Set config defaults once for every test."""
    monkeypatch.setattr(mod.Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large", raising=True)
    monkeypatch.setattr(mod.Config, "UNIFIED_VECTOR_DIM", 1024, raising=True)


@pytest.fixture
def svc(mod):
    """Service with a fake client that returns a 1024-d vector."""
    fake_client = _FakeOpenAI(_FakeEmbeddingsOK(length=1024))
    return mod.CloudEmbeddingService(client=fake_client)


def test_create_embedding_ok(svc):
    emb = svc.create_embedding("Title | Desc | Skopje | Tech | 2025-09-01 | Organizer")
    assert isinstance(emb, list)
    assert len(emb) == 1024


def test_provider_exception_wrapped(mod):
    fake_client = _FakeOpenAI(_FakeEmbeddingsRaise(Exception("boom")))
    svc = mod.CloudEmbeddingService(client=fake_client)
    with pytest.raises(mod.EmbeddingServiceException, match="OpenAI embedding request failed"):
        svc.create_embedding("some text")


def test_unexpected_payload_wrapped(mod):
    fake_client = _FakeOpenAI(_FakeEmbeddingsEmpty())
    svc = mod.CloudEmbeddingService(client=fake_client)
    with pytest.raises(mod.EmbeddingServiceException, match="unexpected embedding payload"):
        svc.create_embedding("whatever")


def test_mismatched_dimension_raises(mod):
    # Return a vector with the wrong length (100)
    fake_client = _FakeOpenAI(_FakeEmbeddingsOK(length=100))
    svc = mod.CloudEmbeddingService(client=fake_client)
    with pytest.raises(mod.EmbeddingServiceException, match=r"Expected 1024-dim embedding, got 100"):
        svc.create_embedding("ok")


def test_empty_text_rejected(svc, mod):
    with pytest.raises(mod.EmbeddingServiceException, match="non-empty string"):
        svc.create_embedding("   ")
