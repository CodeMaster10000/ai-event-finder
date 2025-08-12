from typing import List, Dict

from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService
from app.services.model.model_service import ModelService
from app.configuration.config import Config
from ollama import Client
from app.util.format_event_util import format_event


class LocalModelService(ModelService):
    """
    Implementation of the ModelService using a local Ollama embedder + chat LLM,
    plus PGVector-based retrieval of relevant events.
    """

    def __init__(
        self,
        event_repository: EventRepository,
        embedding_service: EmbeddingService,
        client: Client, # DI-provided Ollama LLM client
        sys_prompt: str | None = None,
    ):
        super().__init__(event_repository, embedding_service, sys_prompt=sys_prompt)
        self.client = client

    def query_prompt(self, user_prompt: str) -> str:
        """
        1) Retrieve RAG context (embedding + events)
        2) Build full chat messages
        3) Call the Ollama chat API and return assistant text
        """
        # 1) fetch context
        rag_context = self.get_rag_data_and_create_context(user_prompt)

        # 2) assemble messages
        messages = self.build_messages(self.sys_prompt, rag_context, user_prompt)

        resp = self.client.chat(
            model=Config.OLLAMA_LLM,
            messages=messages,
            options=Config.OLLAMA_LLM_OPTIONS
        )
        # Ollama python client returns: {"message": {"content": "..."}}
        return resp["message"]["content"].strip()

    def build_messages(
        self,
        sys_prompt: str,
        context: str,
        user_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Assemble a chat-ready list of messages:
        - system: your base instruction
        - system: the RAG context bullets (if any)
        - user:   the original user prompt
        """
        msgs = [
                {"role": "system", "content": f"{sys_prompt}\n\n{context}"},
                {"role": "user", "content": user_prompt}
        ]
        return msgs

    def get_rag_data_and_create_context(self, user_prompt: str) -> str:
        """
        1) Embed the user_prompt via embedding_service
        2) Fetch top-K similar events
        3) Format into bullet-list string
        """
        # 1) embed the user prompt
        embed_vector = self.embedding_service.create_embedding(user_prompt)

        # 2) retrieve most fit events
        events = self.event_repository.search_by_embedding(embed_vector, Config.RAG_TOP_K)

        # 3) format events
        formatted = [format_event(e) for e in events]

        return "\n".join(formatted)
