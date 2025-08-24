from __future__ import annotations

from typing import List, Dict, Any, cast, Optional

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.configuration.config import Config
from poetry.console.commands import self
from app.extensions import db
from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService
from app.services.model.model_service import ModelService
from app.util.format_event_util import format_event
from app.util.logging_util import log_calls
from app.util.model_util import COUNT_EXTRACT_SYS_PROMPT


@log_calls("app.services")
class ModelServiceImpl(ModelService):
    """
    ModelService implementation that:
      - uses your existing EmbeddingService + EventRepository for RAG
      - calls an OpenAI-hosted chat LLM for generation

    Public API preserved:
      - __init__(event_repository, embedding_service, client, sys_prompt=None)
      - query_prompt(user_prompt) -> str
      - build_messages(sys_prompt, context, user_prompt) -> List[ChatCompletionMessageParam]
      - get_rag_data_and_create_context(user_prompt) -> str
    """

    def __init__(
        self,
        event_repository: EventRepository,
        embedding_service: EmbeddingService,
        client: AsyncOpenAI,  # DI-provided async OpenAI client
        model: str | None = None,
        sys_prompt: Optional[str] = None,
    ):
        # Calls the ModelService constructor (keeps existing behavior)

        super().__init__(event_repository, embedding_service, sys_prompt=sys_prompt)
        self.client = client
        self.model = model or (Config.DMR_LLM_MODEL if Config.PROVIDER == "local"
        else Config.OPENAI_MODEL)

    # ---------------------------
    # Public API
    # ---------------------------
    async def query_prompt(self, user_prompt: str) -> str:
        """
        1) Embed the user prompt via embedding_service
        2) Fetch top-K similar events and format them
        3) Build chat messages
        4) Call OpenAI Chat Completion API
        5) Return the assistant response
        """
        # 1) embed the user prompt (await if using async embedding service)
        embed_vector = await self.embedding_service.create_embedding(user_prompt)
        print("I got the embedding vector.")
        # 2) retrieve most fit events
        events = self.event_repository.search_by_embedding(query_vector=embed_vector, k=Config.DEFAULT_K_EVENTS, session=db.session)
        # 2) retrieve the most relevant events

        event_count_k = await self.extract_requested_event_count(user_prompt)

        events = self.event_repository.search_by_embedding(embed_vector, event_count_k, 10)
        print("I got the events")
        # 3) format events
        rag_context = "\n".join([format_event(e) for e in events])
        print("I have the RAG context")
        # 4) assemble messages
        messages: List[ChatCompletionMessageParam] = self.build_messages(
            self.sys_prompt, rag_context, user_prompt
        )
        print("I built the messages.")
        # 5) call OpenAI Chat Completions API
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_GEN_OPTS", {}) or {})
        cfg_opts.pop("stream", None)  # remove streaming if present

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **cfg_opts,
        )
        print("I got the answer from OpenAI")
        # defensive extraction
        msg = (resp.choices[0].message.content if resp.choices and resp.choices[0].message else None) or ""
        return msg.strip()

    def build_messages(
        self,
        sys_prompt: Optional[str],
        context: str,
        user_prompt: str,
    ) -> List[ChatCompletionMessageParam]:
        """
        Assemble a chat-ready list of messages:
        - system: base instruction + the RAG context
        - user:   the original user prompt
        """
        sys_text = (sys_prompt or "").strip()
        ctx_text = (context or "no events retrieved").strip()

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

    async def extract_requested_event_count(self, user_prompt: str) -> int:
        """
        Async version: Calls the OpenAI Chat Completions API safely, avoiding duplicate kwargs like 'stream'.
        Returns an integer depicting the requested event count.
        """

        # Start from config opts; ensure it's a dict
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_EXTRACT_K_OPTS", {}) or {})
        cfg_opts.pop("stream", None)  # remove streaming if present


        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{COUNT_EXTRACT_SYS_PROMPT}\n\n".strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": user_prompt,
        }
        messages = [system_msg, user_msg]

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **cfg_opts,
        )

        # defensive extraction
        content = (resp.choices[0].message.content
                   if resp.choices and resp.choices[0].message else "0")

        return int(content.strip())
