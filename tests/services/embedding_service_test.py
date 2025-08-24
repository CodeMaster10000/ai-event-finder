import pytest
import asyncio
from app.container import Container
from app.configuration.config import Config
from app.error_handler.exceptions import EmbeddingServiceException


@pytest.fixture
def embedding_service():
    c = Container()
    return c.embedding_service()


def test_embedding_single_text_dimension(embedding_service):
    vec = asyncio.run(embedding_service.create_embedding("dimension check"))
    assert isinstance(vec, list)
    assert len(vec) == Config.UNIFIED_VECTOR_DIM


@pytest.mark.parametrize("txt", ["hello world", "quick brown fox", "Skopje tech events"])
def test_embedding_multiple_texts_dimension(embedding_service, txt):
    vec = asyncio.run(embedding_service.create_embedding(txt))
    assert isinstance(vec, list)
    assert len(vec) == Config.UNIFIED_VECTOR_DIM


def test_embedding_rejects_empty_input(embedding_service):
    with pytest.raises(EmbeddingServiceException):
        asyncio.run(embedding_service.create_embedding("   "))
