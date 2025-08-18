from __future__ import annotations

from typing import List, Dict, Any, cast, Optional

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
from app.util.model_util import COUNT_EXTRACT_SYS_PROMPT


class CloudModelService(ModelService):
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
        client: OpenAI,  # DI-provided OpenAI client
        sys_prompt: Optional[str] = None,
    ):
        # Calls the ModelService constructor (keeps existing behavior)
        super().__init__(event_repository, embedding_service, sys_prompt=sys_prompt)
        self.client = client

    # ---------------------------
    # Public API
    # ---------------------------

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

        # 3) call OpenAI (non-streaming by default; safe against duplicate kwargs)
        text = self._generate_text(messages)
        return text

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

    # ---------------------------
    # Internals
    # ---------------------------

    def _generate_text(self, messages: List[ChatCompletionMessageParam]) -> str:
        """
        Calls the OpenAI Chat Completions API safely, avoiding duplicate kwargs like 'stream'.
        Returns plain string content (non-streaming aggregation if you ever enable streaming).
        """
        model = getattr(Config, "OPENAI_MODEL", "gpt-4o-mini")

        # Start from config opts; ensure it's a dict
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_GEN_OPTS", {}) or {})

        # We always return a final string from this method.
        # If 'stream' appears in config, remove it so we don't double-pass and to keep this path non-streaming.
        # (If you later want streaming, create a separate method that yields chunks.)
        cfg_opts.pop("stream", None)

        # Optional: set a sane default timeout if supported via 'timeout' in your HTTP client config.
        # (OpenAI SDK uses 'max_retries' and timeouts in client config; leaving here for clarity.)
        # cfg_opts.setdefault("timeout", 60)

        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **cfg_opts,
        )

        # Defensive extraction
        msg = (resp.choices[0].message.content if resp.choices and resp.choices[0].message else None) or ""
        return msg.strip()

    def extract_requested_event_count(self, user_prompt: str) -> int:
        """
            Calls the OpenAI Chat Completions API safely, avoiding duplicate kwargs like 'stream'.
            Returns an integer depicting the requested event count.
        """
        model = getattr(Config, "OPENAI_MODEL", "gpt-4o-mini")

        # Start from config opts; ensure it's a dict
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_EXTRACT_K_OPTS", {}) or {})

        # We always return a final integer from this method.
        # If 'stream' appears in config, remove it so we don't double-pass and to keep this path non-streaming.
        cfg_opts.pop("stream", None)


        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{COUNT_EXTRACT_SYS_PROMPT}\n\n".strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": user_prompt,
        }
        messages=[system_msg, user_msg]

        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **cfg_opts,
        )

        return int(resp.choices[0].message.content)



