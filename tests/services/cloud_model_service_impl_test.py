import os
import pytest
import asyncio
from app.container import Container
from app.configuration.config import Config

pytest.skip("Skipping AI calls", allow_module_level=True)
# -------- Helpers -------------------------------------------------------------

def _default_k():
    return int(getattr(Config, "DEFAULT_K_EVENTS", getattr(Config, "RAG_TOP_K", 5)))

def _max_k():
    return int(getattr(Config, "MAX_K_EVENTS", 20))


# -------- Provider/env wiring (one place only) --------------------------------

@pytest.fixture
def provider_env(monkeypatch, request):
    """
    Parametrized provider setup for DI. Use with @pytest.mark.parametrize('provider', [...])
    Handles DMR base URLs for host vs container runs.
    """
    provider = request.param  # "local" or "cloud"
    monkeypatch.setenv("PROVIDER", provider)

    if provider == "local":
        # Decide how to reach DMR based on where pytest runs:
        # - Host run (Mac/Win): localhost
        # - In-container run: host.docker.internal
        mode = os.getenv("DMR_HOST_MODE", "host")  # "host" or "container"
        chat_base = (
            os.getenv("DMR_CHAT_BASE_URL")
            or ("http://localhost:12434/engines/llama.cpp/v1" if mode == "host"
                else "http://host.docker.internal:12434/engines/llama.cpp/v1")
        )
        embed_base = (
            os.getenv("DMR_EMBED_BASE_URL")
            or ("http://localhost:12434/engines/tei/v1" if mode == "host"
                else "http://host.docker.internal:12434/engines/tei/v1")
        )

        # Required DMR env
        monkeypatch.setenv("DMR_API_KEY", os.getenv("DMR_API_KEY", "dmr"))
        monkeypatch.setenv("DMR_CHAT_BASE_URL", chat_base)
        monkeypatch.setenv("DMR_EMBED_BASE_URL", embed_base)

        # Models: use the names YOUR Config/Container read
        monkeypatch.setenv("DMR_MODEL", os.getenv("DMR_MODEL", "ai/llama3.1:8b-instruct"))
        monkeypatch.setenv("DMR_EMBEDDING_MODEL", os.getenv("DMR_EMBEDDING_MODEL", "ai/mxbai-embed-large:latest"))

    else:
        # Cloud needs an API key; skip if missing
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set; skipping cloud tests")
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
        # Allow overrides; else safe defaults
        monkeypatch.setenv("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"))
        # If you use a custom OpenAI-compatible base_url in cloud, set OPENAI_BASE_URL and make your Container read it.

    # Make extractor deterministic across providers
    monkeypatch.setattr(
        "app.configuration.config.Config.OPENAI_EXTRACT_K_OPTS",
        {"temperature": 0, "top_p": 1, "frequency_penalty": 0,
         "presence_penalty": 0, "max_tokens": 6, "stream": False},
        raising=False,
    )

    # Return the provider to pair with fixtures that depend on it
    return provider


@pytest.fixture
def service(provider_env):
    """
    Build the DI container AFTER env is set, then resolve the model service.
    This ensures the same wiring the app uses (two OpenAI clients in local mode, etc.).
    """
    c = Container()
    svc = c.model_service()

    # Debug print (handy while stabilizing)
    try:
        # Some OpenAI clients expose .base_url; if not, ignore
        base_url = getattr(svc.client, "base_url", None)
        print(f"[test] provider={Config.PROVIDER} base_url={base_url} model={getattr(svc, 'model', None)}")
    except Exception:
        pass

    return svc


# --------- TESTS (run against both providers) ---------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("provider_env", ["local", "cloud"], indirect=True)
@pytest.mark.parametrize(
    "user_prompt,expected",
    [
        ("show me 1 event", 1),
        ("show me 5 events this weekend", 5),
        ("find 7 concerts", 7),
        ("top 10 tech meetups in Skopje", 10),
        ("give me 15 events", 15),
        ("show 20 events", _max_k()),

        ("find one event", 1),
        ("Two DJ sets", 2),
        ("give me three events", 3),
        ("show me four concerts", 4),
        ("find five events", 5),
        ("ten events please", 10),
        ("fifteen events", 15),

        ("Give me Three events", 3),
        ("FIVE events please", 5),
        ("Show me Eight concerts", 8),

        ("what's on 2025-08-15 at 19:00? send 4 events", 4),
        ("events on December 25th at 6pm, show me 3", 3),
        ("what's happening on 2024-12-31 at 23:59? give me 7 events", 7),
        ("August 15th 2025 at 8pm, find 2 events", 2),
        ("events for 01/01/2025 at 12:00, show 6", 6),
        ("2025-03-14 at 15:30 - give me 9 events", 9),
        ("what's on the 25th at 7pm? send 12 events", 12),

        ("$50 tickets, show me 3 events", 3),
        ("events under 20 euros, give me 5", 5),
        ("free to $100 events, find 4", 4),
        ("concerts for 15 dollars or less, show 8", 8),

        ("events near 123 Main Street, show 6", 6),
        ("concerts at venue 42, give me 3", 3),
        ("events in building 15, floor 3, show 2", 2),

        ("events in 2025, show 5", 5),
        ("concerts from 2024, give me 3", 3),
        ("events since 1999, find 7", 7),

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

        ("find events this weekend", _default_k()),
        ("what's happening tonight?", _default_k()),
        ("show me concerts", _default_k()),
        ("jazz events near me", _default_k()),

        ("show me 3-5 events", 5),
        ("give me 3–5 events", 5),
        ("find between 2 and 8 events", 8),
        ("between 1 and 10 concerts", 10),
        ("anywhere from 4 to 7 events", 7),

        ("at least 3 events", 3),
        ("show me at least 5 concerts", 5),
        ("find at least 10 events", 10),
        ("minimum 6 events", 6),
        ("no fewer than 4 events", 4),

        ("up to 8 events", 8),
        ("no more than 5 events", 5),
        ("maximum 12 events", 12),
        ("at most 7 events", 7),
        ("not more than 3 events", 3),

        ("I'm interested in a jazz night... Give me 3 events", 3),
        ("Looking for outdoor summer events... Show me 6 events", 6),
        ("... this Friday. Find 4 events", 4),
        ("family-friendly ... Give me 8 events", 8),

        ("events for 2 people on 2025-12-25, show 5", 5),
        ("3 friends want to see 7 events", 7),
        ("group of 4 looking for 2 events", 2),
        ("6 people, budget $100 each, find 9 events", 9),
        ("team of 10 people wants 3 events", 3),

        ("1st choice events, show me 5", 5),
        ("top 3rd tier events, give me 7", 7),
        ("21st century music, find 4 events", 4),
        ("events on the 15th, show 6", 6),

        ("show me exactly 5 events!", 5),
        ("give me 3 events please.", 3),
        ("find 7 events, thanks", 7),
        ("events (show me 4)", 4),
        ("[6 events please]", 6),
        ("show me #8 events", 8),

        ("show me 0 events", _default_k()),
        ("give me -5 events", _default_k()),

        ("show me 100 events", _max_k()),
        ("find 999 events", _max_k()),
        ("give me 1000 events", _max_k()),

        ("find 3 events, actually make that 5", 5),
        ("show me 10... no wait, 7 events", 7),

        ("twenty-one events", _max_k()),
        ("thirty events", _max_k()),
        ("one hundred events", _max_k()),

        ("room for 50 people, show me 3 events", 3),
        ("event lasts 2 hours, find 5 events", 5),
        ("4 star rated events, show me 8", 8),
        ("events with 100+ attendees, give me 2", 2),

        ("display 5 events", 5),
        ("list 7 events", 7),
        ("present 3 events", 3),
        ("bring up 6 events", 6),
        ("pull 4 events", 4),
        ("fetch 9 events", 9),
        ("retrieve 2 events", 2),

        ("15/08/2025 events, show 4", 4),
        ("08/15/2025 events, give me 6", 6),
        ("15.08.2025 events, find 3", 3),

        ("events at 7:30 AM, show 5", 5),
        ("concerts at 19h30, give me 3", 3),
        ("shows at 8PM, find 4", 4),
        ("events at midnight, show 2", 2),
    ]
)
def test_extract_k_exact_integer(provider_env, service, user_prompt, expected):
    n = asyncio.run(service.extract_requested_event_count(user_prompt))
    assert isinstance(n, int)
    assert n == expected


@pytest.mark.integration
@pytest.mark.parametrize("provider_env", ["local", "cloud"], indirect=True)
def test_extract_k_default_when_no_number(provider_env, service):
    prompt = "recommend some good tech events near me"
    n =  asyncio.run(service.extract_requested_event_count(prompt))
    assert isinstance(n, int)
    assert n == _default_k()


@pytest.mark.integration
@pytest.mark.parametrize("provider_env", ["local", "cloud"], indirect=True)
def test_extract_k_handles_whitespace(provider_env, service):
    prompt = "   please send 12 events \n"
    n = asyncio.run(service.extract_requested_event_count(prompt))
    assert n == 12
