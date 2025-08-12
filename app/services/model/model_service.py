from abc import ABC, abstractmethod
from typing import List, Dict

from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService


class ModelService(ABC):
    """
    Abstract base class for chat-based event querying.
    """

    DEFAULT_SYS_PROMPT = (
        "You are an Event Assistant for a RAG-backed event finder.\n\n"
        "You will receive:\n"
        "- Context: a bullet list of events from the database (only use this information).\n"
        "- User: a single question about events.\n\n"
        "Your job:\n"
        "1) Answer ONLY using the Context — never invent events, details, venues, or times.\n"
        "2) Prefer upcoming events; if none, say so.\n"
        "3) Show up to k top suggestions with: title, date, location, category, and a short reason.\n"
        "4) Be concise, friendly, and deterministic. Avoid markdown tables.\n\n"
        "Formatting:\n"
        "- Start with a short summary.\n"
        "- Then list each event in this format:\n"
        "  1. <Title of the event>:\n"
        "     - Date & Time: <DD Mon YYYY, HH:MM>\n"
        "     - Location: <Location>\n"
        "     - Category: <Event Category>\n"
        "     - Organizer: <Name Surname, Email>\n"
        "     - Short Reason: <Why it matches the user query>\n\n"
        "Safety:\n"
        "- Disambiguate same-title events by date/location.\n"
        "- Never mention internal implementation details."
    )

    def __init__(self,
                 event_repository: EventRepository,
                 embedding_service: EmbeddingService,
                 sys_prompt: str | None = None):
        """Initialize with an EventRepository for vector search."""
        self.event_repository = event_repository
        self.embedding_service = embedding_service
        self.sys_prompt = sys_prompt or self.DEFAULT_SYS_PROMPT

    @abstractmethod
    def query_prompt(self, user_prompt: str) -> str:
        """
        Embed the user prompt, retrieve relevant events, tune hyperparameters, append systemprompt, construct messages,
        and return the assistant's text response.
        """
        ...

    def build_messages(self, context: str, user_prompt: str, sys_prompt) -> List[Dict[str, str]]:
        """
        Assemble the chat messages with system, assistant, and user roles.
        """

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
