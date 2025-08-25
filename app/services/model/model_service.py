from abc import ABC, abstractmethod
from typing import List, Dict

from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService
from app.util.model_util import DEFAULT_SYS_PROMPT


class ModelService(ABC):
    """
    Abstract base class for chat-based event querying.
    """

    def __init__(self,
                 event_repository: EventRepository,
                 embedding_service: EmbeddingService,
                 sys_prompt: str | None = None):
        """Initialize with an EventRepository for vector search."""
        self.event_repository = event_repository
        self.embedding_service = embedding_service
        self.sys_prompt = sys_prompt or DEFAULT_SYS_PROMPT

    @abstractmethod
    async def query_prompt(self, user_prompt: str, session_key: str) -> str:
        """
        Embed the user prompt asynchronously, retrieve relevant events (RAG),
        build chat messages, call an LLM asynchronously, and return the assistant's response.

        Workflow (as implemented in ModelServiceImpl):
        1. Convert the user prompt into an embedding vector using `embedding_service`.
        2. Retrieve the top-K most similar events via `event_repository.search_by_embedding()`.
        3. Format the retrieved events into a readable context string.
        4. Build system + user messages via `build_messages()`.
        5. Call the LLM asynchronously and return the assistant's text response.

        Args:
            user_prompt: The user's input query.

        Returns:
            str: The LLM's assistant response.
        """

    @abstractmethod
    async def extract_requested_event_count(self, user_prompt: str) -> int:
        """
        Async version: Extract the number of events the user is asking for from a free-form prompt.

        This method should call the underlying LLM asynchronously with a dedicated
        **count-extraction** system prompt that coerces the model to output a single integer (no prose).
        Do **not** perform RAG or hit the repositories/embeddings for this operation.

        Args:
            user_prompt: The raw user input (e.g., "show me 5 tech events in Skopje").

        Returns:
            int: The requested event count. If the prompt does not contain a clear,
            positive integer, return the application default (e.g., `K` from env/config).

        Expected behavior / normalization rules:
        - Prefer an explicit positive integer if present (numerals or number words).
        - For ranges or comparative phrases (e.g., "3–5", "up to 7", "at least 10"),
          choose a single reasonable integer (e.g., the most specific bound available);
          if ambiguity remains, fall back to the default.
        - Ignore numerals clearly unrelated to quantity (dates, times, addresses).
        - Clamp to a minimum of 1 if a non-positive value is produced by the LLM.
        - Implementations should be robust to casing, punctuation, and extra text.
        """
