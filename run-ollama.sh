#!/usr/bin/sh

ollama serve &

# Wait for Ollama to be ready (up to 20s)
echo "Waiting for Ollama server to be ready..."
for i in $(seq 1 20); do
    if curl -s http://localhost:11434 > /dev/null; then
        echo "Ollama is up!"
        break
    fi
    sleep 1
done

echo "Pulling model: nomic-embed-text"
ollama pull nomic-embed-text

# Keep the container running (because `ollama serve` is in the background)
tail -f /dev/null
