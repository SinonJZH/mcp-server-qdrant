"""Tests for MCP tool registration, the read-only gate, and the find result format."""

import re

import pytest
from fastmcp import Client

from mcp_server_qdrant.embeddings.fastembed import FastEmbedProvider
from mcp_server_qdrant.mcp_server import QdrantMCPServer
from mcp_server_qdrant.qdrant import Entry
from mcp_server_qdrant.settings import QdrantSettings, ToolSettings


@pytest.fixture
def embedding_provider():
    """Fixture to provide a FastEmbed embedding provider."""
    return FastEmbedProvider(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_server(embedding_provider, read_only: bool = False) -> QdrantMCPServer:
    """Build a QdrantMCPServer backed by in-memory Qdrant."""
    return QdrantMCPServer(
        tool_settings=ToolSettings(),
        # Fields are aliased (validation_alias), so init kwargs must use the aliases
        qdrant_settings=QdrantSettings(
            **{"QDRANT_URL": ":memory:", "QDRANT_READ_ONLY": read_only}
        ),
        embedding_provider=embedding_provider,
    )


async def call_tool_text(server: QdrantMCPServer, name: str, arguments: dict) -> str:
    """Invoke a tool through an in-memory MCP client and return the text output."""
    async with Client(server) as client:
        # In fastmcp 2.x, call_tool returns the content list directly
        result = await client.call_tool(name, arguments)
    return "".join(getattr(content, "text", "") for content in result)


@pytest.mark.asyncio
async def test_read_write_server_exposes_all_tools(embedding_provider):
    """In read/write mode, find, store, update and delete are all registered."""
    server = build_server(embedding_provider, read_only=False)

    tools = await server.get_tools()

    assert set(tools.keys()) == {
        "qdrant-find",
        "qdrant-store",
        "qdrant-update",
        "qdrant-delete",
    }


@pytest.mark.asyncio
async def test_read_only_server_hides_write_tools(embedding_provider):
    """In read-only mode, all write tools (store/update/delete) are hidden."""
    server = build_server(embedding_provider, read_only=True)

    tools = await server.get_tools()

    assert set(tools.keys()) == {"qdrant-find"}


def test_format_entry_includes_id_and_score(embedding_provider):
    """Formatted find results carry the point ID and score alongside content."""
    server = build_server(embedding_provider)
    entry = Entry(
        id="4f8e2c6a-0000-0000-0000-000000000001",
        content="hello world",
        metadata={"topic": "greeting"},
        score=0.8312,
    )

    formatted = server.format_entry(entry)

    assert "<id>4f8e2c6a-0000-0000-0000-000000000001</id>" in formatted
    assert "<score>0.8312</score>" in formatted
    assert "<content>hello world</content>" in formatted
    assert '"topic": "greeting"' in formatted


@pytest.mark.asyncio
async def test_find_delete_flow_via_tools(embedding_provider):
    """End-to-end: find returns point IDs that qdrant-delete accepts."""
    server = build_server(embedding_provider)
    collection = f"flow_{id(embedding_provider)}"

    await call_tool_text(
        server,
        "qdrant-store",
        {
            "information": "nginx static assets are served directly",
            "collection_name": collection,
            "metadata": {"topic": "web"},
        },
    )
    find_output = await call_tool_text(
        server, "qdrant-find", {"query": "nginx", "collection_name": collection}
    )

    assert "<score>" in find_output
    match = re.search(r"<id>([^<]+)</id>", find_output)
    assert match is not None, f"no point ID in find output: {find_output}"
    point_id = match.group(1)

    delete_output = await call_tool_text(
        server,
        "qdrant-delete",
        {"point_ids": [point_id], "collection_name": collection},
    )

    assert f"Deleted 1 entry from collection {collection}" in delete_output
    assert point_id in delete_output

    find_after = await call_tool_text(
        server, "qdrant-find", {"query": "nginx", "collection_name": collection}
    )
    assert "<id>" not in find_after


@pytest.mark.asyncio
async def test_update_flow_via_tools(embedding_provider):
    """End-to-end: update replaces content in place and keeps the point ID."""
    server = build_server(embedding_provider)
    collection = f"update_{id(embedding_provider)}"

    await call_tool_text(
        server,
        "qdrant-store",
        {"information": "old knowledge base entry", "collection_name": collection},
    )
    find_output = await call_tool_text(
        server,
        "qdrant-find",
        {"query": "knowledge base entry", "collection_name": collection},
    )
    point_id = re.search(r"<id>([^<]+)</id>", find_output).group(1)

    update_output = await call_tool_text(
        server,
        "qdrant-update",
        {
            "point_id": point_id,
            "information": "new knowledge base entry",
            "collection_name": collection,
            "metadata": {"replaced": True},
        },
    )

    assert f"Updated: {point_id} in collection {collection}" in update_output

    find_after = await call_tool_text(
        server,
        "qdrant-find",
        {"query": "knowledge base entry", "collection_name": collection},
    )
    assert find_after.count("<id>") == 1  # updated in place, no duplicate
    assert "new knowledge base entry" in find_after


@pytest.mark.asyncio
async def test_update_tool_reports_missing_point(embedding_provider):
    """Updating a nonexistent point ID returns a non-destructive error message."""
    server = build_server(embedding_provider)
    collection = f"missing_{id(embedding_provider)}"

    update_output = await call_tool_text(
        server,
        "qdrant-update",
        {
            "point_id": "00000000-0000-0000-0000-000000000000",
            "information": "irrelevant",
            "collection_name": collection,
        },
    )

    assert "Nothing was updated" in update_output
