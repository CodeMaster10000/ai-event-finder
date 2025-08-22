from __future__ import annotations

from typing import List, Dict, Any, cast, Optional

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.repositories.chat_history_repository import ChatHistoryRepository, Message
from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService
from app.services.model.model_service import ModelService
from app.configuration.config import Config
from app.util.format_event_util import format_event
from app.util.model_util import COUNT_EXTRACT_SYS_PROMPT

MAX_HISTORY_IN_CONTEXT = 5  # include up to last 5 prior messages in CONTEXT


class ModelServiceImpl(ModelService):
    """
    Uses EmbeddingService + EventRepository for RAG, calls OpenAI for generation,
    and (optionally) maintains per-session chat history via ChatHistoryRepository.
    """

    def __init__(
        self,
        event_repository: EventRepository,
        embedding_service: EmbeddingService,
        client: OpenAI,  # DI-provided OpenAI client
        model: str | None = None,
        sys_prompt: Optional[str] = None,
        history_repo: Optional[ChatHistoryRepository] = None,
    ):
        super().__init__(event_repository, embedding_service, sys_prompt=sys_prompt)
        self.client = client
        self.model = model or (Config.DMR_LLM_MODEL if Config.PROVIDER == "local" else Config.OPENAI_MODEL)
        self.history_repo = history_repo

    # ---------------------------
    # Public API
    # ---------------------------

    def query_prompt(self, user_prompt: str, session_key: Optional[str] = None) -> str:
        """
        Build CONTEXT for every request as:
          DOCUMENTS (RAG top-K) + RECENT MESSAGES (last <= 5)
        Send only [system, user]. Then append {user, assistant} to history.
        """
        combined_context = self._build_context_with_history(user_prompt, session_key)

        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": (self.sys_prompt or "").strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"CONTEXT:\n{combined_context}\n\nUSER PROMPT:\n{user_prompt}",
        }
        messages: List[ChatCompletionMessageParam] = cast(List[ChatCompletionMessageParam], [system_msg, user_msg])

        answer = self._generate_text(messages)

        # Persist conversational turns for next time
        if session_key and self.history_repo:
            self.history_repo.append(session_key, "user", user_prompt)
            self.history_repo.append(session_key, "assistant", answer)

        return answer

    def build_messages(
        self,
        sys_prompt: Optional[str],
        context: str,
        user_prompt: str,
    ) -> List[ChatCompletionMessageParam]:
        """
        Stateless helper (kept for compatibility): system(sys+context) + user.
        """
        sys_text = (sys_prompt or "").strip()
        ctx_text = (context or "no events retrieved").strip()

        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{sys_text}\n\n{ctx_text}".strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_prompt}
        return cast(List[ChatCompletionMessageParam], [system_msg, user_msg])

    def get_rag_data_and_create_context(self, user_prompt: str) -> str:
        """
        1) Embed the user prompt
        2) Retrieve top-K similar events
        3) Format into newline-joined context
        """
        embed_vector = self.embedding_service.create_embedding(user_prompt)
        events = self.event_repository.search_by_embedding(embed_vector, Config.RAG_TOP_K)
        formatted = [format_event(e) for e in events]
        return "\n".join(formatted)

    # ---------------------------
    # Internals
    # ---------------------------

    def _build_context_with_history(self, user_prompt: str, session_key: Optional[str]) -> str:
        """Combine RAG documents + last <=5 prior messages into one CONTEXT string."""
        rag_docs = self.get_rag_data_and_create_context(user_prompt)

        history_block = ""
        count = 0
        if session_key and self.history_repo:
            prior: List[Message] = self.history_repo.get(session_key)
            recent = prior[-MAX_HISTORY_IN_CONTEXT:] if prior else []
            count = len(recent)
            if recent:
                # Compact, line-per-message format
                lines = [
                    f"{m['role']}: {m['content']}".strip()
                    for m in recent
                    if m.get("role") and m.get("content")
                ]
                history_block = "\n".join(lines)

        parts: List[str] = []
        if rag_docs.strip():
            parts.append(f"DOCUMENTS:\n{rag_docs}")
        if history_block:
            parts.append(f"RECENT MESSAGES (last {count}):\n{history_block}")

        return "\n\n".join(parts) if parts else "No context available."

    def _generate_text(self, messages: List[ChatCompletionMessageParam]) -> str:
        """
        Calls the OpenAI Chat Completions API (non-streaming) and returns content.
        """
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_GEN_OPTS", {}) or {})
        cfg_opts.pop("stream", None)  # ensure non-streaming path here

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **cfg_opts,
        )
        msg = (resp.choices[0].message.content if resp.choices and resp.choices[0].message else None) or ""
        return msg.strip()

    def extract_requested_event_count(self, user_prompt: str) -> int:
        """
        Ask the model to extract a requested count value.
        """
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_EXTRACT_K_OPTS", {}) or {})
        cfg_opts.pop("stream", None)

        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{COUNT_EXTRACT_SYS_PROMPT}\n\n".strip(),
        }
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_prompt}
        messages = [system_msg, user_msg]

        resp = self.client.chat.completions.create(model=self.model, messages=messages, **cfg_opts)
        return int(resp.choices[0].message.content)
