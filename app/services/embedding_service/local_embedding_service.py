import os
import requests
from .embedding_service import EmbeddingService
from app.configuration.config import Config
from app.models.event import Event
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
        prompt = self._format_event(event_data)
        response = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": model, "prompt": prompt},
        )
        response.raise_for_status()
        result = response.json()
        return result["embedding"]

    def _format_event(self, event: Event) -> str:
        """
        Format an Event object into a string prompt to send to the embedding model.

        Args:
            event (Event): Event object from the database.

        Returns:
            str: Formatted string representing the event.
        """
        fields = [
            event.title or "",
            event.description or "",
            event.location or "",
            event.category or "",
            event.datetime.isoformat() if event.datetime else "",
            str(event.organizer) if event.organizer else "",  # You could also use organizer.name or email
        ]

        return " | ".join(fields)
