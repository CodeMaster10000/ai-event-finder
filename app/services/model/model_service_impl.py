from __future__ import annotations

from typing import List, Dict, Any, cast, Optional

from openai import AsyncOpenAI
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



class ModelServiceImpl(ModelService):
    """
    Uses EmbeddingService + EventRepository for RAG, calls OpenAI for generation,
    and (optionally) maintains per-session chat history via ChatHistoryRepository.
    """

    def __init__(
        self,
        event_repository: EventRepository,
        embedding_service: EmbeddingService,
        client: AsyncOpenAI,  # DI-provided OpenAI client
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

    async def query_prompt(self, user_prompt: str, session_key: Optional[str] = None) -> str:
        """
        1) Embed prompt
        2) Decide K (requested or default) and retrieve top-K events
        3) Build CONTEXT = DOCUMENTS + last ≤5 history lines
        4) Build messages [system, user(CONTExt+prompt)] and call OpenAI
        5) Append {user, assistant} to history
        """
        # 1) embed the user prompt (await if using async embedding service)
        embed_vector = await self.embedding_service.create_embedding(user_prompt)

        # 2) retrieve most fit events
        k = await self.extract_requested_event_count(user_prompt)
        events = self.event_repository.search_by_embedding(embed_vector, k, 10)
        rag_docs = "\n".join([format_event(e) for e in events])

        # 3) build recent history snippet (last ≤5)
        history_block = ""
        count = 0
        if session_key and self.history_repo:
            prior: List[Message] = self.history_repo.get(session_key)
            recent = prior[-Config.MAX_HISTORY_IN_CONTEXT:] if prior else []
            count = len(recent)
            if recent:
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
        combined_context = "\n\n".join(parts) if parts else "No context available."

        # 4) assemble messages and call OpenAI
        messages: List[ChatCompletionMessageParam] = self.build_messages(
            self.sys_prompt, combined_context, user_prompt
        )
        cfg_opts: Dict[str, Any] = dict(getattr(Config, "OPENAI_GEN_OPTS", {}) or {})
        cfg_opts.pop("stream", None)  # ensure non-streaming here

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **cfg_opts,
        )
        answer = (resp.choices[0].message.content if resp.choices and resp.choices[0].message else "") or ""
        answer = answer.strip()

        # 5) persist {user, assistant} for next turn
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
