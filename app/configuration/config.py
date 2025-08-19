import os
from dotenv import load_dotenv, find_dotenv

# Locates the path of the .env file and loads it
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# Loads PostgresSQL connection URI and other settings from environment variables, defined in a .env file.
class Config:
    PROVIDER = os.getenv("PROVIDER", "local").lower()

    DMR_BASE_URL = os.getenv("DMR_BASE_URL", "http://host.docker.internal:12434/v1")
    DMR_EMBEDDING_MODEL = os.getenv("DMR_EMBEDDING_MODEL", "ai/mxbai-embed-large")
    DMR_MODEL = os.getenv("DMR_LLM_MODEL", "ai/llama3.1:8b-instruct")
    DMR_API_KEY = os.getenv("DMR_API_KEY", "dmr")

    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    DEFAULT_K_EVENTS = int(os.getenv("DEFAULT_K_EVENTS", "5"))
    MAX_K_EVENTS = int(os.getenv("MAX_K_EVENTS", "5"))

    DMR_TEMPERATURE = float(os.getenv("DMR_TEMPERATURE", 0.3))
    DMR_TOP_P = float(os.getenv("DMR_TOP_P", 0.9))
    DMR_TOP_K = int(os.getenv("DMR_TOP_K", 30))
    DMR_NUM_PREDICT = int(os.getenv("DMR_NUM_PREDICT", 256))
    DMR_SEED = int(os.getenv("DMR_SEED", 42))



    OLLAMA_LLM_OPTIONS = {
        "temperature": DMR_TEMPERATURE,
        "top_p": DMR_TOP_P,
        "top_k": DMR_TOP_K,
        "num_predict": DMR_NUM_PREDICT,
        "seed": DMR_SEED
    }

    OLLAMA_LLM_EXTRACT_K_OPTIONS = { #HARDCODED FOR TESTING
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 1,
        "num_predict": 6,
        "seed": DMR_SEED
    }

    # CLOUD
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))
    OPENAI_P = float(os.getenv("OPENAI_P"))
    FREQUENCY_PENALTY = float(os.getenv("OPENAI_FREQUENCY_PENALTY"))
    PRESENCE_PENALTY = float(os.getenv("OPENAI_PRESENCE_PENALTY"))
    MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS"))

    OPENAI_MODEL = str(os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    OPENAI_GEN_OPTS = {
        "temperature" : OPENAI_TEMPERATURE,
        "top_p": OPENAI_P,
        "frequency_penalty" : FREQUENCY_PENALTY,
        "presence_penalty" : PRESENCE_PENALTY,
        "max_tokens" : MAX_TOKENS,
        "stream" : True
    }

    OPENAI_EXTRACT_K_OPTS = { #hard coded for testing
        "temperature": 0,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "max_tokens": 6,
        "stream": False
    }


    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "hard-coded-test-key")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    # One shared size we standardize on for the DB vector column (e.g., 1024)
    UNIFIED_VECTOR_DIM = int(os.getenv("UNIFIED_VECTOR_DIM", 1024))

print("Using DB user:", os.getenv("DB_USER"))
