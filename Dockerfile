# Vendors jayasree's runtime files from npm — kept out of the app image's
# git history and layer, only the copied output below makes it into the final stage.
FROM node:20-slim AS jsbuild
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY scripts/sync_jayasree.sh ./scripts/sync_jayasree.sh
RUN bash scripts/sync_jayasree.sh

FROM ghcr.io/sachn1/linguaalayam-base:latest

WORKDIR /app

RUN pip install --no-cache-dir poetry

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock README.md ./

# Install production deps (torch already in base image from pytorch-cpu source)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev,huggingface --no-root --no-interaction

# Copy application source and Alembic migrations
COPY linguaalayam/ ./linguaalayam/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY --from=jsbuild /app/linguaalayam/static/vendor ./linguaalayam/static/vendor

# Install the package itself
RUN poetry install --without dev,huggingface --no-interaction

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

EXPOSE 8000

CMD ["python", "-c", "from linguaalayam.api.app import main; main()"]
