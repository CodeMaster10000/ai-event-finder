import os
from dotenv import load_dotenv, find_dotenv

# Locates the path of the .env file and loads it
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# Loads PostgreSQL connection URI and other settings from environment variables, defined in a .env file.
class Config:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

print("Using DB user:", os.getenv("DB_USER"))
