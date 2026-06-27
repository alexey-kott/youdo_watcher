FROM python:3.13-slim AS builder

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /code

# Copy dependency manifests and lock file
COPY pyproject.toml uv.lock ./

# Install Python dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project


FROM python:3.13-slim AS runtime

WORKDIR /code

# Copy the virtual environment from builder
COPY --from=builder /code/.venv /code/.venv
ENV PATH="/code/.venv/bin:$PATH"

# Install Playwright Chromium with its system dependencies
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY app/ /code/app/

# Copy queries file
COPY queries.txt /code/queries.txt

# Set default environment (can be overridden at runtime)
ENV APP_QUERIES_FILE=queries.txt

CMD ["python", "-m", "app.watcher"]
