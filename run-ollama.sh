#!/usr/bin/env bash
set -e

MODEL="${OLLAMA_EMBEDDING_MODEL}"

echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama server to be ready by checking if `ollama list` works
echo "Waiting for Ollama server to become available..."
until ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama server is up."
echo "Pulling model: $MODEL"
ollama pull "$MODEL"

# Keep container running
wait
