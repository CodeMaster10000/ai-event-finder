import os
import openai
from .embedding_service import EmbeddingService
from app.util.event_util import format_event
from app.models.event import Event

# Configure OpenAI API key and model (hard-coded fallback until you switch to .env)
openai.api_key = os.getenv("OPENAI_API_KEY", "hard-coded-test-key")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


class CloudEmbeddingService(EmbeddingService):
    """
    Generates vector embeddings for Event objects using OpenAI's Embedding API.
    """

    def create_embedding(self, event_data: Event) -> list[float]:
        """
        Format the event into text, call OpenAI's embedding endpoint,
        and return the resulting vector.

        Args:
            event_data (Event): The event to embed.

        Returns:
            list[float]: The 1,024-dim embedding vector.
        """
        # 1. Build the input text from the Event
        prompt = format_event(event_data)

        # 2. Request an embedding from OpenAI
        response = openai.Embedding.create(
            model=EMBEDDING_MODEL,
            input=prompt
        )

        # 3. Extract and return the embedding vector
        data = response.get("data", [])
        if not data:
            raise ValueError("OpenAI did not return any embeddings.")
        return data[0]["embedding"]
