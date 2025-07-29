# Use the official slim Python 3.13 image as the base
FROM python:3.13-slim

# Upgrade pip and install Poetry (Python dependency manager)
RUN pip install --upgrade pip \
    && pip install poetry

# Set the working directory inside the container to /app
WORKDIR /app

# Copy dependency files to the container (used to install packages)
COPY pyproject.toml poetry.lock* /app/

# Configure Poetry to install packages globally (no venv), then install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of the project files into the container
COPY . /app

# Expose port 5000 (Flask default) so it can be mapped outside
EXPOSE 5000

# Run the Flask app using run.py when the container starts
CMD ["python", "run.py"]
