from abc import ABC, abstractmethod

class EmbeddingService(ABC):
    """
    Abstract base class for generating vector embeddings from string input.

    Implementations should:
    - Accept a plain string (e.g., a prompt, event description, etc.)
    - Generate and return a numerical embedding as a list of floats

    This abstraction allows embedding providers (local or cloud-based) to be
    swapped without modifying application logic.
    """

    @abstractmethod
    async def create_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector from input text.

        Args:
            text (str): The input text to embed (e.g., prompt, formatted event)

        Returns:
            list[float]: A numerical vector embedding of the input.
        """
        pass
