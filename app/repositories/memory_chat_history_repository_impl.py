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
            return self._store.setdefault(key, [])

    def set(self, key: str, messages: List[Message]) -> None:
        with self._lock:
            self._store[key] = messages

    def append(self, key: str, role: str, content: str) -> None:
        with self._lock:
            hist = self._store.setdefault(key, [])
            hist.append({"role": role, "content": content})
            if len(hist) > self._max:
                system = [m for m in hist if m["role"] == "system"]
                rest = [m for m in hist if m["role"] != "system"][-(self._max - len(system)):]
                self._store[key] = system + rest
