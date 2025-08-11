import requests

from app.configuration.config import Config
from .embedding_service import EmbeddingService


class LocalEmbeddingService(EmbeddingService):
    """
    Local embedding service that communicates with a locally running Ollama server
    to generate embeddings from a given string of text.
    """

    def create_embedding(self, text: str) -> list[float]:
        """
        Creates an embedding vector for the given text using the Ollama API.

        Args:
            text (str): A plain text string to embed (e.g., event description or prompt)

        Returns:
            list[float]: The embedding vector as a list of floats.
        """

        response = requests.post(
            f"{Config.OLLAMA_URL}/api/embeddings",
            json={"model": Config.OLLAMA_MODEL, "prompt": text},
        )
        response.raise_for_status()
        result = response.json()
        return result["embedding"]
