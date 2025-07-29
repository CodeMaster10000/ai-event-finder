FROM python:3.13-slim
RUN pip install --upgrade pip \
    && pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock* /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi
COPY . /app
EXPOSE 5000
CMD ["python", "run.py"]