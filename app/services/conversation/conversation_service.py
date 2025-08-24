from typing import List, Dict, Optional
from app.repositories.chat_history_repository import ChatHistoryRepository, Message
from app.services.model.local_model_service_impl import LocalModelServiceImpl
# If you have a RAG retriever, inject it too (embedding/vector store)

class ConversationService:
    def __init__(self, history_repo: ChatHistoryRepository, llm: LocalModelServiceImpl):
        self.history = history_repo
        self.llm = llm

    def _ensure_system(self, key: str, text: str):
        msgs = self.history.get(key)
        if not any(m["role"] == "system" for m in msgs):
            self.history.append(key, "system", text)

    def chat(self, key: str, prompt: str, context: Optional[str] = None) -> str:
        self._ensure_system(key, "You are a helpful assistant. Use CONTEXT if relevant.")

        # Build user content with optional RAG context
        content = f"CONTEXT:\n{context}\n\nUSER PROMPT:\n{prompt}" if context else prompt

        # Prepare full message list for the model (history + new user turn)
        messages: List[Message] = self.history.get(key) + [{"role": "user", "content": content}]

        # Call LLM
        answer = self.llm.chat(messages)

        # Persist this turn to per-user history
        self.history.append(key, "user", prompt)
        self.history.append(key, "assistant", answer)

        return answer
