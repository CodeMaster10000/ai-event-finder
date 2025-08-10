from typing import List
from openai import OpenAI

from .embedding_service import EmbeddingService
from app.configuration.config import Config
from app.util.format_event_util import format_event
from app.models.event import Event

class CloudEmbeddingService(EmbeddingService):
    """
    OpenAI embeddings (text-embedding-3-*, dimensions=1024).
    """

    def __init__(self) -> None:
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_EMBEDDING_MODEL
        self.dim = Config.UNIFIED_VECTOR_DIM  # 1024

    def _embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")
        try:
            resp = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dim,  # request 1024-d output
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI embedding request failed: {e}") from e

        data = getattr(resp, "data", None) or []
        if not data or not hasattr(data[0], "embedding"):
            raise RuntimeError("OpenAI returned no embedding data.")

        emb = data[0].embedding
        if len(emb) != self.dim:
            raise ValueError(f"Expected {self.dim}-dim embedding, got {len(emb)}")
        return list(emb)

    def create_embedding(self, event_data: Event) -> List[float]:
        return self._embed_text(format_event(event_data))

    def create_query_embedding(self, query: str) -> List[float]:
        return self._embed_text(query)
