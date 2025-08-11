from abc import ABC, abstractmethod
from typing import List, Dict

from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService


class ModelService(ABC):
    """
    Abstract base class for chat-based event querying.
    """

    def __init__(self,
                 event_repository: EventRepository,
                 embedding_service: EmbeddingService):
        """Initialize with an EventRepository for vector search."""
        self.event_repository = event_repository
        self.embedding_service = embedding_service
        self.sys_prompt = (
            "You are an Event Assistant for a RAG-backed event finder. You will receive:\n\n"
            "- Context: a bullet list of events retrieved from the database (this is the ONLY source of truth).\n"
            "- User: the end-user’s question.\n\n"
            "Data fields you may see per event: title, datetime (ISO or human date), location, category, description, organizer.\n\n"
            "Your job:\n"
            "1) Answer ONLY using the events in Context. Never invent events, details, venues, or times.\n"
            "2) Prefer upcoming events (future datetime) over past ones. If none are upcoming, say so and offer the most relevant past results with clear labeling.\n"
            "3) Show at most 3 top suggestions unless the user explicitly asks for more.\n"
            "4) For each suggestion include: title, date (DD Mon YYYY, 24h time if present), city/location, and 1 short reason why it fits the user’s query (derived from Context).\n"
            "5) If the user’s query is vague (no date/place/genre), briefly ask 1 clarifying question AFTER giving a safe starter suggestion.\n"
            "6) If Context is empty or irrelevant, say you don’t have matching events and suggest how to refine the query (e.g., date range, city, category). Do not hallucinate.\n"
            "7) Be concise, friendly, and deterministic. Avoid markdown tables. Use simple bullets or short paragraphs.\n"
            "8) If the user asks for sorting/filters (date, location, category), apply them using ONLY the Context.\n"
            "9) If the user asks about details not present in Context, say it’s not provided.\n\n"
            "Formatting:\n"
            "- Start with a one-line summary (e.g., “Here are a few options for tonight in Skopje”).\n"
            "- Then list up to 3 items:\n"
            "  • <Title> — <DD Mon YYYY, HH:MM> — <Location>. <1-line reason>\n"
            "- If you ask a clarifying question, put it at the end as a single short sentence.\n\n"
            "Safety & edge cases:\n"
            "- Deduplicate near-identical events.\n"
            "- If multiple events share the same title, disambiguate by date/location.\n"
            "- If user asks for tomorrow/tonight/weekend, interpret relative dates based on the provided datetimes in Context; if ambiguous, ask once.\n"
            "- Never mention internal implementation details (embeddings, vectors, PGVector, etc.).\n"
        )

    @abstractmethod
    def query_prompt(self, user_prompt: str) -> str:
        """
        Embed the user prompt, retrieve relevant events, tune hyperparameters, append systemprompt, construct messages,
        and return the assistant's text response.
        """
        #TODO implement this here
        ...

    def build_messages(self, context: str, user_prompt: str, sys_prompt) -> List[Dict[str, str]]:
        """
        Assemble the chat messages with system, assistant, and user roles.
        """
        #TODO implement this here

    def get_rag_data_and_create_context(self, user_prompt) -> List[Dict[str, str]]:
        #TODO implement this here
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
