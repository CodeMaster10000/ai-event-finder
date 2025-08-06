from abc import ABC, abstractmethod
from app.models.event import Event

class EmbeddingService(ABC):
    """
    Abstract base class for generating vector embeddings from event data.

    This service defines the interface for embedding generation and is intended
    to be implemented by concrete embedding backends such as local embedding
    models (e.g., SentenceTransformers) or cloud-based embedding providers
    (e.g., OpenAI, Azure, Cohere).

    Implementations should:
    - Accept an Event Object with event attributes (e.g., title, description, location, etc.)
    - Convert these attributes into a suitable format for the embedding model
    - Generate and return a numerical embedding as a list of floats

    Note:
        This abstraction allows the rest of the application (e.g., event creation service)
        to remain decoupled from the specific embedding implementation and switch between
        local and cloud backends with minimal change.
    """

    @abstractmethod
    def create_embedding(self, event_data: Event) -> list[float]:
        """
        Generate an embedding vector from event data.

        Args:
            event_data (dict): Dictionary containing event fields like title, description,
                               datetime, location, category, etc.

        Returns:
            list[float]: A numerical vector embedding of the event.
        """
        pass