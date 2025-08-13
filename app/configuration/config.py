import os
from dotenv import load_dotenv, find_dotenv

# Locates the path of the .env file and loads it
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# Loads PostgresSQL connection URI and other settings from environment variables, defined in a .env file.
class Config:
    # LOCAL
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-large")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")
    OLLAMA_LLM = os.getenv("OLLAMA_LLM", "llama3.1")

    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", 0.3))
    OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", 0.9))
    OLLAMA_TOP_K = int(os.getenv("OLLAMA_TOP_K", 30))
    OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", 256))
    OLLAMA_SEED = int(os.getenv("OLLAMA_SEED", 42))

    OLLAMA_LLM_OPTIONS = {
        "temperature": OLLAMA_TEMPERATURE,
        "top_p": OLLAMA_TOP_P,
        "top_k": OLLAMA_TOP_K,
        "num_predict": OLLAMA_NUM_PREDICT,
        "seed": OLLAMA_SEED
    }

    # CLOUD
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))
    OPENAI_P = float(os.getenv("OPENAI_P"))
    FREQUENCY_PENALTY = float(os.getenv("OPENAI_FREQUENCY_PENALTY"))
    PRESENCE_PENALTY = float(os.getenv("OPENAI_PRESENCE_PENALTY"))
    MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS"))

    OPENAI_MODEL = str(os.getenv("OPENAI_MODEL"))
    OPENAI_GEN_OPTS = {
        "temperature" : OPENAI_TEMPERATURE,
        "top_p": OPENAI_P,
        "frequency_penalty" : FREQUENCY_PENALTY,
        "presence_penalty" : PRESENCE_PENALTY,
        "max_tokens" : MAX_TOKENS,
        "stream" : True
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
