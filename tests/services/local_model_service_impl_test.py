import os
import pytest
from unittest.mock import MagicMock
from ollama import Client

from app.configuration.config import Config
from app.services.model.local_model_service_impl import LocalModelService
from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService

pytest.skip("Skipping LLM tests.", allow_module_level=True)

# -------------------- Connectivity helpers --------------------

def _ollama_base_url() -> str:
    """
    Priority:
      1) OLLAMA_TEST_URL (explicit override for tests)
      2) Config.OLLAMA_URL if present
      3) OLLAMA_EMBEDDING_URL (your fallback in Config)
      4) http://localhost:11434
    """
    return (
        os.getenv("OLLAMA_TEST_URL")
        or getattr(Config, "OLLAMA_URL", None)
        or os.getenv("OLLAMA_EMBEDDING_URL")
        or "http://localhost:11434"
    )


def _model_name() -> str:
    # The model tag tests will ask Ollama to run
    return getattr(Config, "OLLAMA_LLM", "llama3.1")


@pytest.fixture(scope="session")
def ollama_client_or_skip():
    """Create a real Ollama client or skip the suite if not available."""
    base = _ollama_base_url()
    client = Client(host=base)

    # 1) Reachability (/api/tags)
    try:
        client.list()
    except Exception as e:
        pytest.skip(f"Ollama not reachable at {base}. Start it (and publish port 11434). Details: {e}")

    # 2) Model availability
    model = _model_name()
    try:
        tags = client.list() or {}
        names = {m.get("name", "") for m in (tags.get("models") or [])}
        if not any(model in n for n in names):
            # Fallback probe
            try:
                client.show(model)
            except Exception as se:
                pytest.skip(f"Model '{model}' not available. Run: `ollama pull {model}`. Details: {se}")
    except Exception as e:
        pytest.skip(f"Could not verify model availability for '{model}'. Details: {e}")

    return client


# -------------------- Service fixture --------------------

@pytest.fixture
def service(ollama_client_or_skip):
    """
    Construct LocalModelService with the real Ollama client.
    Repo/embedding are unused by the extractor, so we pass MagicMocks
    to keep the constructor happy and to assert they aren't invoked.
    """
    mock_repo = MagicMock(spec=EventRepository)
    mock_embed = MagicMock(spec=EmbeddingService)

    return LocalModelService(
        event_repository=mock_repo,
        embedding_service=mock_embed,
        client=ollama_client_or_skip,
    )


# -------------------- Helper for default K in your prompt --------------------

def _default_k():
    return int(getattr(Config, "RAG_TOP_K", 5))
def _max_k():
    return int(getattr(Config, "MAX_K_EVENTS", 5))


# -------------------- LIVE TESTS --------------------

@pytest.mark.integration
@pytest.mark.parametrize(
    "user_prompt,expected",
    [
        # Basic explicit counts - numerals
        ("show me 1 event", 1),
        ("show me 5 events this weekend", 5),
        ("find 7 concerts", 7),
        ("top 10 tech meetups in Skopje", 10),
        ("give me 15 events", 15),
        ("show 20 events", _max_k()),

        # Basic explicit counts - number words
        ("find one event", 1),
        ("Two DJ sets", 2),
        ("give me three events", 3),
        ("show me four concerts", 4),
        ("find five events", 5),
        ("ten events please", 10),
        ("fifteen events", 15),

        # Mixed case number words
        ("Give me Three events", 3),
        ("FIVE events please", 5),
        ("Show me Eight concerts", 8),

        # Date/time with explicit event counts - should ignore date/time
        ("what's on 2025-08-15 at 19:00? send 4 events", 4),
        ("events on December 25th at 6pm, show me 3", 3),
        ("what's happening on 2024-12-31 at 23:59? give me 7 events", 7),
        ("August 15th 2025 at 8:_max_k()pm, find 2 events", 2),
        ("events for 01/01/2025 at 12:00, show 6", 6),
        ("2025-03-14 at 15:30 - give me 9 events", 9),
        ("what's on the 25th at 7pm? send 12 events", 12),

        # Prices/money with event counts - should ignore prices
        ("$50 tickets, show me 3 events", 3),
        ("events under 20 euros, give me 5", 5),
        ("free to $100 events, find 4", 4),
        ("concerts for 15 dollars or less, show 8", 8),

        # Address/location numbers with event counts - should ignore addresses
        ("events near 123 Main Street, show 6", 6),
        ("concerts at venue 42, give me 3", 3),
        ("events in building 15, floor 3, show 2", 2),

        # Years as standalone with event counts - should ignore years
        ("events in 2025, show 5", 5),
        ("concerts from 2024, give me 3", 3),
        ("events since 1999, find 7", 7),

        # Vague quantities - should use default
        ("I want to go to a rock concert. Show me a couple of events", _default_k()),
        ("Give me a couple of cool events in Ohrid!", _default_k()),
        ("recommend some good tech events near me", _default_k()),
        ("A few music conferences", _default_k()),
        ("I want a few concerts", _default_k()),
        ("show me several events", _default_k()),
        ("give me some events", _default_k()),
        ("find many events", _max_k()),
        ("show me a handful of concerts", _default_k()),
        ("give me a bunch of events", _default_k()),
        ("find dozens of events", _max_k()),
        ("show me loads of concerts", _max_k()),
        ("tons of events please", _max_k()),

        # No explicit count - should use default
        ("find events this weekend", _default_k()),
        ("what's happening tonight?", _default_k()),
        ("show me concerts", _default_k()),
        ("jazz events near me", _default_k()),

        # Ranges - should take the higher number
        ("show me 3-5 events", 5),
        ("give me 3–5 events", 5),  # em dash
        ("find between 2 and 8 events", 8),
        ("between 1 and 10 concerts", 10),
        ("anywhere from 4 to 7 events", 7),

        # "At least" patterns - should use the specified number
        ("at least 3 events", 3),
        ("show me at least 5 concerts", 5),
        ("find at least 10 events", 10),
        ("minimum 6 events", 6),
        ("no fewer than 4 events", 4),

        # "Up to" patterns - should use the specified number
        ("up to 8 events", 8),
        ("no more than 5 events", 5),
        ("maximum 12 events", 12),
        ("at most 7 events", 7),
        ("not more than 3 events", 3),

        # Complex sentences with explicit counts
        ("I'm interested in a jazz night. I want to drink cocktails and relax with some friends. Ideally in a nice place. Give me 3 events",
         3),
        ("Looking for outdoor summer events with good music and food. Budget is flexible. Show me 6 events", 6),
        ("My girlfriend loves electronic music and we want to go dancing this Friday. Find 4 events", 4),
        ("Need family-friendly events for kids aged 5-12. Budget under $50 per person. Give me 8 events", 8),

        # Multiple numbers - should pick the event count, not other numbers
        ("events for 2 people on 2025-12-25, show 5", 5),
        ("3 friends want to see 7 events", 7),
        ("group of 4 looking for 2 events", 2),
        ("6 people, budget $100 each, find 9 events", 9),
        ("team of 10 people wants 3 events", 3),

        # Ordinals mixed with counts - should ignore ordinals
        ("1st choice events, show me 5", 5),
        ("top 3rd tier events, give me 7", 7),
        ("21st century music, find 4 events", 4),
        ("events on the 15th, show 6", 6),

        # Edge cases with punctuation and formatting
        ("show me exactly 5 events!", 5),
        ("give me 3 events please.", 3),
        ("find 7 events, thanks", 7),
        ("events (show me 4)", 4),
        ("[6 events please]", 6),
        ("show me #8 events", 8),

        # Negative/zero tests - should use default (assuming your system handles this)
        ("show me 0 events", 0),  # or however you want to handle zero
        ("give me -5 events", _default_k()),  # negative numbers

        # Very large numbers - test boundaries
        ("show me 100 events",_max_k()),
        ("find 999 events",_max_k()),
        ("give me 1000 events",_max_k()),

        # Multiple explicit counts - should use the last/most relevant one
        ("find 3 events, actually make that 5", 5),
        ("show me 10... no wait, 7 events", 7),

        # Spelled out larger numbers (if supported)
        ("twenty-one events", _max_k()),  # should default as it's not in your supported list
        ("thirty events",_max_k()),  # should default
        ("one hundred events",_max_k()),  # should default

        # Ambiguous contexts
        ("room for 50 people, show me 3 events", 3),  # capacity vs event count
        ("event lasts 2 hours, find 5 events", 5),  # duration vs event count
        ("4 star rated events, show me 8", 8),  # rating vs event count
        ("events with 100+ attendees, give me 2", 2),  # attendee count vs event count

        # Different phrasings for event requests
        ("display 5 events", 5),
        ("list 7 events", 7),
        ("present 3 events", 3),
        ("bring up 6 events", 6),
        ("pull 4 events", 4),
        ("fetch 9 events", 9),
        ("retrieve 2 events", 2),

        # International date formats with event counts
        ("15/08/2025 events, show 4", 4),  # DD/MM/YYYY
        ("08/15/2025 events, give me 6", 6),  # MM/DD/YYYY
        ("15.08.2025 events, find 3", 3),  # DD.MM.YYYY

        # Time formats with event counts
        ("events at 7:30 AM, show 5", 5),
        ("concerts at 19h30, give me 3", 3),
        ("shows at 8PM, find 4", 4),
        ("events at midnight, show 2", 2),
    ]
)
def test_live_returns_exact_integer(service, user_prompt, expected):
    n = service.extract_requested_event_count(user_prompt)
    assert isinstance(n, int)
    assert n == expected


@pytest.mark.integration
def test_live_uses_default_when_no_number(service):
    """
    Relies on COUNT_EXTRACT_SYS_PROMPT instructing the model to use the provided default.
    Ensure your system prompt includes something like: 'Default count: {DEFAULT_K}'.
    """
    prompt = "recommend some good tech events near me"
    n = service.extract_requested_event_count(prompt)
    assert isinstance(n, int)
    assert n == _default_k()


@pytest.mark.integration
def test_live_handles_whitespace_and_newlines(service):
    prompt = "   please send 12 events \n"
    n = service.extract_requested_event_count(prompt)
    assert n == 12


