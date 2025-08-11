import os
from dotenv import load_dotenv, find_dotenv

# Locates the path of the .env file and loads it
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# Loads PostgreSQL connection URI and other settings from environment variables, defined in a .env file.
class Config:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")
    OLLAMA_LLM = os.getenv("OLLAMA_LLM", "llama3.1")

    RAG_TOP_K = 5

    OLLAMA_LLM_OPTIONS = {
        "temperature": 0.3, # how random next token is
        "top_p": 0.9, #
        "top_k": 30,
        "num_predict": 256,
        "seed": 42
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
