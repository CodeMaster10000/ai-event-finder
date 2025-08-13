from typing import List, cast

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService
from app.services.model.model_service import ModelService
from app.configuration.config import Config
from app.util.format_event_util import format_event


class CloudModelService(ModelService):
    """
    ModelService implementation that:
      - uses your existing EmbeddingService + EventRepository for RAG
      - calls an OpenAI-hosted chat LLM for generation
    """

    def __init__(
        self,
        event_repository: EventRepository,
        embedding_service: EmbeddingService,
        client: OpenAI,  # DI-provided OpenAI client
        sys_prompt: str | None = None, #optional system prompt
    ):
        super().__init__(event_repository, embedding_service, sys_prompt=sys_prompt) # calls the ModelService constructor
        self.client = client # stores the openai client on the instance

    def query_prompt(self, user_prompt: str) -> str:
        """
        1) Retrieve RAG context (embedding + events)
        2) Build full chat messages
        3) Call the OpenAI Chat Completions API and return assistant text
        """
        # 1) fetch context
        rag_context = self.get_rag_data_and_create_context(user_prompt)

        # 2) assemble messages (typed for OpenAI SDK)
        messages: List[ChatCompletionMessageParam] = self.build_messages(
            self.sys_prompt, rag_context, user_prompt
        )

        # 3) call OpenAI
        resp = self.client.chat.completions.create(
            model=Config.OPENAI_MODEL,  # or annotate OPENAI_MODEL: str in Config
            messages=messages,
            **getattr(Config, "OPENAI_GEN_OPTS", {}),
        )

        # OpenAI response shape: choices[0].message.content
        return resp.choices[0].message.content.strip()

    def build_messages(
        self,
        sys_prompt: str | None,
        context: str,
        user_prompt: str,
    ) -> List[ChatCompletionMessageParam]:
        """
        Assemble a chat-ready list of messages:
        - system: base instruction + the RAG context
        - user:   the original user prompt
        """
        sys_text = (sys_prompt or "").strip()
        ctx_text = (context or "").strip()

        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{sys_text}\n\n{ctx_text}".strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": user_prompt,
        }

        # Cast ensures strict checkers accept the union type list
        return cast(List[ChatCompletionMessageParam], [system_msg, user_msg])

    def get_rag_data_and_create_context(self, user_prompt: str) -> str:
        """
        1) Embed the user_prompt via embedding_service
        2) Fetch top-K similar events
        3) Format into a newline-joined list
        """
        # 1) embed the user prompt
        embed_vector = self.embedding_service.create_embedding(user_prompt)

        # 2) retrieve most fit events
        events = self.event_repository.search_by_embedding(embed_vector, Config.RAG_TOP_K)

        # 3) format events
        formatted = [format_event(e) for e in events]
        return "\n".join(formatted)
