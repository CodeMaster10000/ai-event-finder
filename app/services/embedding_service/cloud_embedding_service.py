from openai import OpenAI
from .embedding_service import EmbeddingService
from app.configuration.config import Config
from app.error_handler.exceptions import EmbeddingServiceException


class CloudEmbeddingService(EmbeddingService):
    """
    OpenAI cloud embedding using text-embedding-3-* with a unified dimension.
    Accepts plain text and returns a list[float], same shape as LocalEmbeddingService.
    """

    def __init__(self, client: OpenAI):
        self.client = client

    def create_embedding(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise EmbeddingServiceException("Input text must be a non-empty string.")

        try:
            resp = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=text,
                dimensions=Config.UNIFIED_VECTOR_DIM,
            )
        except Exception as e:
            raise EmbeddingServiceException("OpenAI embedding request failed.", original_exception=e)

        try:
            emb = resp.data[0].embedding
        except Exception as e:
            raise EmbeddingServiceException("OpenAI returned an unexpected embedding payload.", original_exception=e)

        if len(emb) != Config.UNIFIED_VECTOR_DIM:
            raise EmbeddingServiceException(
                f"Expected {Config.UNIFIED_VECTOR_DIM}-dim embedding, got {len(emb)}"
            )

        return list(emb)