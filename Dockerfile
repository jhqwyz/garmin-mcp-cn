FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["garmin-mcp"]
