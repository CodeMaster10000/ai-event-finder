import pytest
from app.container import Container
from app.configuration.config import Config
from app.error_handler.exceptions import EmbeddingServiceException
pytest.skip("Skipping AI calls", allow_module_level=True)
@pytest.fixture
def embedding_service():
    # Build via DI so it uses the same provider/base_url/models as the app
    c = Container()
    svc = c.embedding_service()
    # Handy debug to catch miswires quickly
    try:
        base_url = getattr(svc.client, "base_url", None)
        print(f"[emb-test] provider={Config.PROVIDER} base_url={base_url} model={getattr(svc, 'model', None)}")
    except Exception:
        pass
    return svc

def test_embedding_single_text_dimension(embedding_service):
    vec = embedding_service.create_embedding("dimension check")
    assert isinstance(vec, list)
    assert len(vec) == Config.UNIFIED_VECTOR_DIM

@pytest.mark.parametrize("txt", ["hello world", "quick brown fox", "Skopje tech events"])
def test_embedding_multiple_texts_dimension(embedding_service, txt):
    vec = embedding_service.create_embedding(txt)
    assert isinstance(vec, list)
    assert len(vec) == Config.UNIFIED_VECTOR_DIM

def test_embedding_rejects_empty_input(embedding_service):
    with pytest.raises(EmbeddingServiceException):
        embedding_service.create_embedding("   ")
