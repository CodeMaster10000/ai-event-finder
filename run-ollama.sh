#!/usr/bin/env bash
set -e

EMBEDDING_MODEL="${EMBEDDING_MODEL_NAME}"
LLM_MODEL="${LLM_MODEL_NAME}"

if [ -z "$EMBEDDING_MODEL" ]; then
  echo "EMBEDDING_MODEL_NAME not set"
  exit 1
fi


if [ -z "$LLM_MODEL" ]; then
  echo "LLM_MODEL_NAME not set"
  exit 1
fi

echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama server to be ready by checking if `ollama list` works
echo "Waiting for Ollama server to become available..."
until ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama server is up."
echo "Pulling embedding model: $EMBEDDING_MODEL"
ollama pull "$EMBEDDING_MODEL"

echo "Pulling Large Language model: $LLM_MODEL"
ollama pull "$LLM_MODEL"


# Keep container running
wait
