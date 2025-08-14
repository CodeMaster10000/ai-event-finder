from datetime import datetime

from app.services.embedding_service.local_embedding_service import LocalEmbeddingService
from app.util.format_event_util import format_event
from app.models.event import Event


def test_real_embedding_call():

    test_event = Event(
        title="OpenAI Conference",
        description="Annual conference on artificial intelligence.",
        location="San Francisco, CA",
        category="Technology",
        datetime=datetime(2025, 8, 6, 9, 0, 0),
        organizer_id = 1
    )

    service = LocalEmbeddingService()
    embedding = service.create_embedding(format_event(test_event))

    print(f"Embedding vector (length {len(embedding)}):")
    print(embedding)

if __name__ == "__main__":
    test_real_embedding_call()
