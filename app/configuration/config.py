import os
from dotenv import load_dotenv, find_dotenv

# Locates the path of the .env file and loads it
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

# Loads PostgresSQL connection URI and other settings from environment variables, defined in a .env file.
class Config:
    PROVIDER = os.getenv("PROVIDER", "local").lower()

    DMR_BASE_URL = os.getenv("DMR_CHAT_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1")
    DMR_EMBEDDING_MODEL = os.getenv("DMR_EMBEDDING_MODEL", "ai/mxbai-embed-large")
    DMR_LLM_MODEL = os.getenv("DMR_LLM_MODEL", "ai/llama3.1:8b-instruct")
    DMR_API_KEY = os.getenv("DMR_API_KEY", "dmr")

    DEFAULT_K_EVENTS = int(os.getenv("DEFAULT_K_EVENTS", 5))
    MAX_K_EVENTS = int(os.getenv("MAX_K_EVENTS", 5))

    # CLOUD
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))
    OPENAI_P = float(os.getenv("OPENAI_P"))
    FREQUENCY_PENALTY = float(os.getenv("OPENAI_FREQUENCY_PENALTY"))
    PRESENCE_PENALTY = float(os.getenv("OPENAI_PRESENCE_PENALTY"))
    MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS"))

    OPENAI_EXTRACT_TEMPERATURE = float(os.getenv("OPENAI_EXTRACT_TEMPERATURE"))
    OPENAI_EXTRACT_P = float(os.getenv("OPENAI_EXTRACT_P"))
    OPENAI_EXTRACT_FREQUENCY_PENALTY = float(os.getenv("OPENAI_EXTRACT_FREQUENCY_PENALTY"))
    OPENAI_EXTRACT_PRESENCE_PENALTY = float(os.getenv("OPENAI_EXTRACT_PRESENCE_PENALTY"))
    OPENAI_EXTRACT_MAX_TOKENS = int(os.getenv("OPENAI_EXTRACT_MAX_TOKENS"))

    OPENAI_GEN_OPTS = {
        "temperature" : OPENAI_TEMPERATURE,
        "top_p": OPENAI_P,
        "frequency_penalty" : FREQUENCY_PENALTY,
        "presence_penalty" : PRESENCE_PENALTY,
        "max_tokens" : MAX_TOKENS,
        "stream" : True
    }

    OPENAI_EXTRACT_K_OPTS = { #hard coded for testing
        "temperature": OPENAI_TEMPERATURE,
        "top_p": OPENAI_TEMPERATURE,
        "frequency_penalty": OPENAI_EXTRACT_FREQUENCY_PENALTY,
        "presence_penalty": OPENAI_EXTRACT_PRESENCE_PENALTY,
        "max_tokens": OPENAI_EXTRACT_MAX_TOKENS,
        "stream": False
    }

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "hard-coded-test-key")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    OPENAI_MODEL = str(os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # --- DB URI with TEST_MODE respected (unset => false) ---
    if _get_bool("TEST_MODE", False):
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{os.getenv('TEST_DB_USER')}:{os.getenv('TEST_DB_PASSWORD')}"
            f"@{os.getenv('TEST_DB_HOST')}:{os.getenv('TEST_DB_PORT')}/{os.getenv('TEST_DB_NAME')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 50))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 50))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))  # seconds to wait for a free conn
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))  # recycle after 30 min
    DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() in ("1", "true", "yes", "on")

    MAX_HISTORY_IN_CONTEXT = int(os.getenv("MAX_HISTORY_IN_CONTEXT", 5))

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": DB_POOL_SIZE,
        "max_overflow": DB_MAX_OVERFLOW,
        "pool_timeout": DB_POOL_TIMEOUT,
        "pool_recycle": DB_POOL_RECYCLE,
        "pool_pre_ping": DB_POOL_PRE_PING,
    }

    # One shared size we standardize on for the DB vector column (e.g., 1024)
    UNIFIED_VECTOR_DIM = int(os.getenv("UNIFIED_VECTOR_DIM", 1024))

print("Using DB user:", os.getenv("DB_USER"))
