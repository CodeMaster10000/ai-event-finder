import threading
from typing import List, Dict
from .chat_history_repository import ChatHistoryRepository, Message

class MemoryChatHistoryRepository(ChatHistoryRepository):
    def __init__(self, max_messages: int = 50):
        self._store: Dict[str, List[Message]] = {}
        self._lock = threading.Lock()
        self._max = max_messages

    def get(self, key: str) -> List[Message]:
        with self._lock:
            return list(self._store.get(key, []))

    def set(self, key: str, messages: List[Message]) -> None:
        with self._lock:
            self._store[key] = list(messages)[-self._max:]

    def append(self, key: str, role: str, content: str) -> None:
        with self._lock:
            hist = self._store.setdefault(key, [])
            hist.append({"role": role, "content": content})
            if len(hist) > self._max:
                self._store[key] = hist[-self._max:]
