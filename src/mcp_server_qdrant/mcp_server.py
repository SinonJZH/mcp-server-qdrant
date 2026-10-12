import json
import logging
from typing import Annotated, Any, Optional

from fastmcp import Context, FastMCP
from pydantic import Field
from qdrant_client import models

from mcp_server_qdrant.common.filters import make_indexes
from mcp_server_qdrant.common.func_tools import make_partial_function
from mcp_server_qdrant.common.wrap_filters import wrap_filters
from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.embeddings.factory import create_embedding_provider
from mcp_server_qdrant.qdrant import ArbitraryFilter, Entry, Metadata, QdrantConnector
from mcp_server_qdrant.settings import (
    EmbeddingProviderSettings,
    QdrantSettings,
    ToolSettings,
)

logger = logging.getLogger(__name__)


# FastMCP is an alternative interface for declaring the capabilities
# of the server. Its API is based on FastAPI.
class QdrantMCPServer(FastMCP):
    """
    A MCP server for Qdrant.
    """

    def __init__(
        self,
        tool_settings: ToolSettings,
        qdrant_settings: QdrantSettings,
        embedding_provider_settings: Optional[EmbeddingProviderSettings] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        name: str = "mcp-server-qdrant",
        instructions: str | None = None,
        **settings: Any,
    ):
        self.tool_settings = tool_settings
        self.qdrant_settings = qdrant_settings

        if embedding_provider_settings and embedding_provider:
            raise ValueError(
                "Cannot provide both embedding_provider_settings and embedding_provider"
            )

        if not embedding_provider_settings and not embedding_provider:
            raise ValueError(
                "Must provide either embedding_provider_settings or embedding_provider"
            )

        self.embedding_provider_settings: Optional[EmbeddingProviderSettings] = None
        self.embedding_provider: Optional[EmbeddingProvider] = None

        if embedding_provider_settings:
            self.embedding_provider_settings = embedding_provider_settings
            self.embedding_provider = create_embedding_provider(
                embedding_provider_settings
            )
        else:
            self.embedding_provider_settings = None
            self.embedding_provider = embedding_provider

        assert self.embedding_provider is not None, "Embedding provider is required"

        self.qdrant_connector = QdrantConnector(
            qdrant_settings.location,
            qdrant_settings.api_key,
            qdrant_settings.collection_name,
            self.embedding_provider,
            qdrant_settings.local_path,
            make_indexes(qdrant_settings.filterable_fields_dict()),
        )

        super().__init__(name=name, instructions=instructions, **settings)

        self.setup_tools()

    def format_entry(self, entry: Entry) -> str:
        """
        Feel free to override this method in your subclass to customize the format of the entry.
        """
        entry_id = f"<id>{entry.id}</id>" if entry.id else ""
        entry_score = (
            f"<score>{entry.score:.4f}</score>" if entry.score is not None else ""
        )
        entry_metadata = json.dumps(entry.metadata) if entry.metadata else ""
        return (
            f"<entry>{entry_id}{entry_score}"
            f"<content>{entry.content}</content><metadata>{entry_metadata}</metadata></entry>"
        )

    def setup_tools(self):
        """
        Register the tools in the server.
        """

        async def store(
            ctx: Context,
            information: Annotated[str, Field(description="Text to store")],
            collection_name: Annotated[
                str, Field(description="The collection to store the information in")
            ],
            # The `metadata` parameter is defined as non-optional, but it can be None.
            # If we set it to be optional, some of the MCP clients, like Cursor, cannot
            # handle the optional parameter correctly.
            metadata: Annotated[
                Metadata | None,
                Field(
                    description="Extra metadata stored along with memorised information. Any json is accepted."
                ),
            ] = None,
        ) -> str:
            """
            Store some information in Qdrant.
            :param ctx: The context for the request.
            :param information: The information to store.
            :param metadata: JSON metadata to store with the information, optional.
            :param collection_name: The name of the collection to store the information in, optional. If not provided,
                                    the default collection is used.
            :return: A message indicating that the information was stored.
            """
            await ctx.debug(f"Storing information {information} in Qdrant")

            entry = Entry(content=information, metadata=metadata)

            await self.qdrant_connector.store(entry, collection_name=collection_name)
            if collection_name:
                return f"Remembered: {information} in collection {collection_name}"
            return f"Remembered: {information}"

        async def find(
            ctx: Context,
            query: Annotated[str, Field(description="What to search for")],
            collection_name: Annotated[
                str, Field(description="The collection to search in")
            ],
            query_filter: ArbitraryFilter | None = None,
        ) -> list[str] | None:
            """
            Find memories in Qdrant.
            :param ctx: The context for the request.
            :param query: The query to use for the search.
            :param collection_name: The name of the collection to search in, optional. If not provided,
                                    the default collection is used.
            :param query_filter: The filter to apply to the query.
            :return: A list of entries found or None.
            """

            # Log query_filter
            await ctx.debug(f"Query filter: {query_filter}")

            query_filter = models.Filter(**query_filter) if query_filter else None

            await ctx.debug(f"Finding results for query {query}")

            entries = await self.qdrant_connector.search(
                query,
                collection_name=collection_name,
                limit=self.qdrant_settings.search_limit,
                query_filter=query_filter,
            )
            if not entries:
                return None
            content = [
                f"Results for the query '{query}'",
            ]
            for entry in entries:
                content.append(self.format_entry(entry))
            return content

        async def update(
            ctx: Context,
            point_id: Annotated[
                str,
                Field(
                    description="The point ID of the entry to update, as returned by qdrant-find"
                ),
            ],
            information: Annotated[
                str, Field(description="The new text content of the entry")
            ],
            collection_name: Annotated[
                str, Field(description="The collection the entry belongs to")
            ],
            # The `metadata` parameter is defined as non-optional, but it can be None.
            # If we set it to be optional, some of the MCP clients, like Cursor, cannot
            # handle the optional parameter correctly.
            metadata: Annotated[
                Metadata | None,
                Field(
                    description="New metadata to store along with the entry. Any json is accepted. Replaces any previously stored metadata."
                ),
            ] = None,
        ) -> str:
            """
            Update an existing entry in Qdrant in place, identified by its point ID.
            The entry content is re-embedded with the configured embedding model and
            the point keeps its ID. Nothing is changed if the point ID does not exist.
            :param ctx: The context for the request.
            :param point_id: The point ID of the entry to update.
            :param information: The new text content of the entry.
            :param collection_name: The name of the collection the entry belongs to, optional. If not provided,
                                    the default collection is used.
            :param metadata: New JSON metadata to store with the entry, optional.
            :return: A message indicating whether the entry was updated.
            """
            await ctx.debug(f"Updating entry {point_id} in Qdrant")

            entry = Entry(content=information, metadata=metadata)

            updated = await self.qdrant_connector.update(
                entry, point_id=point_id, collection_name=collection_name
            )
            if not updated:
                return (
                    f"Nothing was updated: point {point_id} was not found in "
                    f"collection {collection_name}. Use qdrant-find to get valid point IDs."
                )
            return f"Updated: {point_id} in collection {collection_name}"

        async def delete(
            ctx: Context,
            point_ids: Annotated[
                list[str],
                Field(
                    description="The point ID(s) of the entries to delete, as returned by qdrant-find"
                ),
            ],
            collection_name: Annotated[
                str, Field(description="The collection the entries belong to")
            ],
        ) -> str:
            """
            Delete entries from Qdrant, identified by their point IDs. Deletion is
            irreversible, so confirm with the user before calling this tool. The
            deleted entries' content is returned for verification.
            :param ctx: The context for the request.
            :param point_ids: The point IDs of the entries to delete.
            :param collection_name: The name of the collection the entries belong to, optional. If not provided,
                                    the default collection is used.
            :return: A message listing the deleted entries and any IDs that were not found.
            """
            await ctx.debug(f"Deleting entries {point_ids} from Qdrant")

            deleted_entries, missing_ids = await self.qdrant_connector.delete(
                point_ids, collection_name=collection_name
            )
            lines: list[str] = []
            if deleted_entries:
                count = len(deleted_entries)
                lines.append(
                    f"Deleted {count} {'entry' if count == 1 else 'entries'} "
                    f"from collection {collection_name}:"
                )
                for entry in deleted_entries:
                    preview = entry.content[:100] + (
                        "..." if len(entry.content) > 100 else ""
                    )
                    lines.append(f"  - {entry.id}: {preview}")
            if missing_ids:
                lines.append(
                    f"No point found for ID(s) {', '.join(missing_ids)} "
                    f"in collection {collection_name}; nothing was deleted for them."
                )
            if not lines:
                return (
                    f"Nothing was deleted: none of the given point IDs exist in "
                    f"collection {collection_name}."
                )
            return "\n".join(lines)

        find_foo = find
        store_foo = store
        update_foo = update
        delete_foo = delete

        filterable_conditions = (
            self.qdrant_settings.filterable_fields_dict_with_conditions()
        )

        if len(filterable_conditions) > 0:
            find_foo = wrap_filters(find_foo, filterable_conditions)
        elif not self.qdrant_settings.allow_arbitrary_filter:
            find_foo = make_partial_function(find_foo, {"query_filter": None})

        if self.qdrant_settings.collection_name:
            find_foo = make_partial_function(
                find_foo, {"collection_name": self.qdrant_settings.collection_name}
            )
            store_foo = make_partial_function(
                store_foo, {"collection_name": self.qdrant_settings.collection_name}
            )
            update_foo = make_partial_function(
                update_foo, {"collection_name": self.qdrant_settings.collection_name}
            )
            delete_foo = make_partial_function(
                delete_foo, {"collection_name": self.qdrant_settings.collection_name}
            )

        self.tool(
            find_foo,
            name="qdrant-find",
            description=self.tool_settings.tool_find_description,
        )

        if not self.qdrant_settings.read_only:
            # Those methods can modify the database
            self.tool(
                store_foo,
                name="qdrant-store",
                description=self.tool_settings.tool_store_description,
            )
            self.tool(
                update_foo,
                name="qdrant-update",
                description=self.tool_settings.tool_update_description,
            )
            self.tool(
                delete_foo,
                name="qdrant-delete",
                description=self.tool_settings.tool_delete_description,
            )
