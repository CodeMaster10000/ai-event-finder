# tests/services/cloud_model_service_impl_test.py
import os
import pytest
from unittest.mock import MagicMock
from openai import OpenAI

from app.configuration.config import Config
from app.services.model.cloud_model_service_impl import CloudModelService
from app.repositories.event_repository import EventRepository
from app.services.embedding_service.embedding_service import EmbeddingService


# -------------------- Cloud (OpenAI) prechecks --------------------

@pytest.fixture(scope="session")
def openai_client_or_skip():
    """Create a real OpenAI client or skip if API key/model not configured."""
    api_key = os.getenv("OPENAI_API_KEY") or getattr(Config, "OPENAI_API_KEY", None)
    model = os.getenv("OPENAI_MODEL") or getattr(Config, "OPENAI_MODEL", None)

    if not api_key:
        pytest.skip("OPENAI_API_KEY not set in environment/.env")
    if not model:
        pytest.skip("OPENAI_MODEL not set (e.g., gpt-4o-mini). Add it to .env")

    # Instantiate using env; SDK will pick up OPENAI_API_KEY automatically
    try:
        client = OpenAI()
    except Exception as e:
        pytest.skip(f"Failed to init OpenAI client: {e}")
    return client


# -------------------- Force deterministic decoding for this suite --------------------

@pytest.fixture(autouse=True)
def force_deterministic_openai(monkeypatch):
    """
    Make the cloud extractor deterministic regardless of OPENAI_GEN_OPTS in Config.
    The service merges from Config, so we override that dict here.
    """
    opts = dict(getattr(Config, "OPENAI_GEN_OPTS", {}) or {})
    # Hard overrides for extractor behavior
    opts.update({
        "temperature": 0,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "max_tokens": 12,          # single integer; short & safe
        "stream": False,
        "stop": ["\n", "Assistant:", "User:"],  # keep it to one-line integer
    })
    # Patch the config used by CloudModelService
    monkeypatch.setattr("app.configuration.config.Config.OPENAI_GEN_OPTS", opts, raising=False)


# -------------------- Service fixture (real cloud client, no DB/RAG) --------------------

@pytest.fixture
def service(openai_client_or_skip):
    """
    Construct CloudModelService with the real OpenAI client.
    Repo/embedding are unused by the extractor; use MagicMocks to satisfy ctor.
    """
    mock_repo = MagicMock(spec=EventRepository)
    mock_embed = MagicMock(spec=EmbeddingService)
    return CloudModelService(
        event_repository=mock_repo,
        embedding_service=mock_embed,
        client=openai_client_or_skip,
    )


# -------------------- Helpers for defaults/caps --------------------

def _default_k():
    # Prefer DEFAULT_K_EVENTS if you set it; else fall back to RAG_TOP_K; else 5.
    return int(getattr(Config, "DEFAULT_K_EVENTS", getattr(Config, "RAG_TOP_K", 5)))

def _max_k():
    # If you cap max results, expose MAX_K_EVENTS; else default to 20 for these tests.
    return int(getattr(Config, "MAX_K_EVENTS", 20))


# -------------------- LIVE TESTS (Cloud) --------------------

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

        # Date/time with explicit counts
        ("what's on 2025-08-15 at 19:00? send 4 events", 4),
        ("events on December 25th at 6pm, show me 3", 3),
        ("what's happening on 2024-12-31 at 23:59? give me 7 events", 7),
        ("August 15th 2025 at 8pm, find 2 events", 2),  # fixed typo from original
        ("events for 01/01/2025 at 12:00, show 6", 6),
        ("2025-03-14 at 15:30 - give me 9 events", 9),
        ("what's on the 25th at 7pm? send 12 events", 12),

        # Prices/money with event counts
        ("$50 tickets, show me 3 events", 3),
        ("events under 20 euros, give me 5", 5),
        ("free to $100 events, find 4", 4),
        ("concerts for 15 dollars or less, show 8", 8),

        # Address/location numbers
        ("events near 123 Main Street, show 6", 6),
        ("concerts at venue 42, give me 3", 3),
        ("events in building 15, floor 3, show 2", 2),

        # Years with event counts
        ("events in 2025, show 5", 5),
        ("concerts from 2024, give me 3", 3),
        ("events since 1999, find 7", 7),

        # Vague quantities -> default (requires your ambiguous-word guard or strict prompt)
        ("I want to go to a rock concert. Show me a couple of events", _default_k()),
        ("Give me a couple of cool events in Ohrid!", _default_k()),
        ("recommend some good tech events near me", _default_k()),
        ("A few music conferences", _default_k()),
        ("I want a few concerts", _default_k()),
        ("show me several events", _default_k()),
        ("give me some events", _default_k()),
        ("find many events", _max_k()),      # if you map 'many' to cap; adjust if you prefer default
        ("show me a handful of concerts", _default_k()),
        ("give me a bunch of events", _default_k()),
        ("find dozens of events", _max_k()),
        ("show me loads of concerts", _max_k()),
        ("tons of events please", _max_k()),

        # No explicit count -> default
        ("find events this weekend", _default_k()),
        ("what's happening tonight?", _default_k()),
        ("show me concerts", _default_k()),
        ("jazz events near me", _default_k()),

        # Ranges -> upper bound
        ("show me 3-5 events", 5),
        ("give me 3–5 events", 5),
        ("find between 2 and 8 events", 8),
        ("between 1 and 10 concerts", 10),
        ("anywhere from 4 to 7 events", 7),

        # "At least" -> N
        ("at least 3 events", 3),
        ("show me at least 5 concerts", 5),
        ("find at least 10 events", 10),
        ("minimum 6 events", 6),
        ("no fewer than 4 events", 4),

        # "Up to" -> N
        ("up to 8 events", 8),
        ("no more than 5 events", 5),
        ("maximum 12 events", 12),
        ("at most 7 events", 7),
        ("not more than 3 events", 3),

        # Complex sentences
        ("I'm interested in a jazz night... Give me 3 events", 3),
        ("Looking for outdoor summer events... Show me 6 events", 6),
        ("... this Friday. Find 4 events", 4),
        ("family-friendly ... Give me 8 events", 8),

        # Multiple numbers -> event count wins
        ("events for 2 people on 2025-12-25, show 5", 5),
        ("3 friends want to see 7 events", 7),
        ("group of 4 looking for 2 events", 2),
        ("6 people, budget $100 each, find 9 events", 9),
        ("team of 10 people wants 3 events", 3),

        # Ordinals in context (ignored)
        ("1st choice events, show me 5", 5),
        ("top 3rd tier events, give me 7", 7),
        ("21st century music, find 4 events", 4),
        ("events on the 15th, show 6", 6),

        # Punctuation & formatting
        ("show me exactly 5 events!", 5),
        ("give me 3 events please.", 3),
        ("find 7 events, thanks", 7),
        ("events (show me 4)", 4),
        ("[6 events please]", 6),
        ("show me #8 events", 8),

        # Negative/zero (adjust to your product rules)
        ("show me 0 events", _default_k()),
        ("give me -5 events", _default_k()),

        # Very large -> cap
        ("show me 100 events", _max_k()),
        ("find 999 events", _max_k()),
        ("give me 1000 events", _max_k()),

        # Multiple explicit counts -> take last/most relevant
        ("find 3 events, actually make that 5", 5),
        ("show me 10... no wait, 7 events", 7),

        # Larger number words not in whitelist -> cap/default
        ("twenty-one events", _max_k()),
        ("thirty events", _max_k()),
        ("one hundred events", _max_k()),

        # Ambiguous contexts with extra numbers
        ("room for 50 people, show me 3 events", 3),
        ("event lasts 2 hours, find 5 events", 5),
        ("4 star rated events, show me 8", 8),
        ("events with 100+ attendees, give me 2", 2),

        # Alternate verbs
        ("display 5 events", 5),
        ("list 7 events", 7),
        ("present 3 events", 3),
        ("bring up 6 events", 6),
        ("pull 4 events", 4),
        ("fetch 9 events", 9),
        ("retrieve 2 events", 2),

        # International dates
        ("15/08/2025 events, show 4", 4),
        ("08/15/2025 events, give me 6", 6),
        ("15.08.2025 events, find 3", 3),

        # Times
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
    prompt = "recommend some good tech events near me"
    n = service.extract_requested_event_count(prompt)
    assert isinstance(n, int)
    assert n == _default_k()


@pytest.mark.integration
def test_live_handles_whitespace_and_newlines(service):
    prompt = "   please send 12 events \n"
    n = service.extract_requested_event_count(prompt)
    assert n == 12
