from openai import AsyncOpenAI
from .embedding_service import EmbeddingService
from app.configuration.config import Config
from app.error_handler.exceptions import EmbeddingServiceException


class EmbeddingServiceImpl(EmbeddingService):
    """
    Async OpenAI embedding service using text-embedding-3-* models with a unified dimension.
    Accepts plain text and returns a list[float], fully non-blocking under ASGI.
    """

    def __init__(self, client: AsyncOpenAI, model: str | None = None):
        self.client = client  # Must be AsyncOpenAI
        self.model = model or (
            Config.DMR_EMBEDDING_MODEL if Config.PROVIDER == "local"
            else Config.OPENAI_EMBEDDING_MODEL
        )

    async def create_embedding(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise EmbeddingServiceException("Input text must be a non-empty string.")

        try:
            # Async call using AsyncOpenAI client
            resp = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=Config.UNIFIED_VECTOR_DIM,
            )
        except Exception as e:
            raise EmbeddingServiceException(
                "OpenAI embedding request failed.", original_exception=e
            )

        try:
            emb = resp.data[0].embedding
        except Exception as e:
            raise EmbeddingServiceException(
                "OpenAI returned an unexpected embedding payload.", original_exception=e
            )

        if len(emb) != Config.UNIFIED_VECTOR_DIM:
            raise EmbeddingServiceException(
                f"Expected {Config.UNIFIED_VECTOR_DIM}-dim embedding, got {len(emb)}"
            )

        return list(emb)
