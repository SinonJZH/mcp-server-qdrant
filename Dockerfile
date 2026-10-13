FROM python:3.12-slim-bookworm

# uv pinned to the version the lockfile is maintained with; `uv sync --frozen`
# installs exactly the versions locked in uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

WORKDIR /app

# Install the locked dependency set first, so this layer only rebuilds when
# pyproject.toml / uv.lock change
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Install the project from this repository's source (NOT the PyPI package —
# the PyPI package is the upstream one and does not contain this fork's tools)
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    FASTMCP_SERVER_HOST=0.0.0.0 \
    FASTMCP_SERVER_PORT=8000

EXPOSE 8000

CMD ["mcp-server-qdrant", "--transport", "streamable-http"]
