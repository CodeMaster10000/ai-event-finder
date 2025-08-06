from app.services.embedding_service.local_embedding_service import LocalEmbeddingService

def test_real_embedding_call():
    event_data = {
        "title": "OpenAI Conference",
        "description": "Annual conference on artificial intelligence.",
        "location": "San Francisco, CA",
        "category": "Technology",
        "datetime": "2025-08-06T09:00:00",
        "organizer": "OpenAI"
    }

    service = LocalEmbeddingService()
    embedding = service.create_embedding(event_data)

    print(f"Embedding vector (length {len(embedding)}):")
    print(embedding)

if __name__ == "__main__":
    test_real_embedding_call()
