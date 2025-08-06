import os
import requests
from .embedding_service import EmbeddingService
from app.configuration.config import Config
from app.models.event import Event
from app.util.event_util import format_event
class LocalEmbeddingService(EmbeddingService):


    def create_embedding(self, event_data: Event) -> list[float]:
        """
               Creates an embedding vector for the given event data using the Ollama API.

               Args:
                   event_data (dict): Dictionary with event fields like title, description, location, etc.

               Returns:
                   list[float]: The embedding vector as a list of floats.
               """

        base_url = Config.OLLAMA_URL
        model = Config.OLLAMA_MODEL
        prompt = format_event(event_data)
        response = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": model, "prompt": prompt},
        )
        response.raise_for_status()
        result = response.json()
        return result["embedding"]

