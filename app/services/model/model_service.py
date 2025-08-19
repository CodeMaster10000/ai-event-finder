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
    def query_prompt(self, user_prompt: str) -> str:
        """
        Embed the user prompt, retrieve relevant events, tune hyperparameters, append systemprompt, construct messages,
        and return the assistant's text response.
        """
        ...

    @abstractmethod
    def build_messages(self, context: str, user_prompt: str, sys_prompt) -> List[Dict[str, str]]:
        """
        Assemble the chat messages with system, assistant, and user roles.
        """

    @abstractmethod
    def get_rag_data_and_create_context(self, user_prompt) -> List[Dict[str, str]]:
        """
        Retrieves relevant event data using a Retrieval-Augmented Generation (RAG) approach
        and constructs a context-aware message list for downstream processing (e.g., LLM input).

        Args:
            sys_prompt (str): A system-level prompt or instruction to be included in the message context.

        Returns:
            List[dict]: A list of formatted messages (typically for LLM input), containing:
                - A system message with event context derived from the most relevant results.
                - A user message with the original user query.

        Workflow:
            1. The method first converts the `user_prompt` into an embedding vector using `get_embedding()`.
            2. It then retrieves the top-N most similar events from `self.event_repository`
               using the `search_by_embedding()` method.
            3. It formats the results into a readable bullet-point list, including each event's
               name, type, location, and time.
            4. It calls `self.build_messages()` to build a message history with the system and user prompts.

        Example of formatted context:
            * AI Conference Talk @ New York (2024-09-10)
            * Hackathon Competition @ San Francisco (2024-09-11)

        This method is useful in RAG-based applications to inject real-world data context into
        LLM queries.
        """

    @abstractmethod
    def extract_requested_event_count(self, user_prompt: str) -> int:
        """
        Extract the number of events the user is asking for from a free-form prompt.

        This method should call the underlying LLM with a dedicated **count-extraction**
        system prompt that coerces the model to output a single integer (no prose).
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

