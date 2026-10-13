# mcp-server-qdrant: A Qdrant MCP server

[中文](README.md) | English

> [!IMPORTANT]
> This repository is a **feature-enhanced fork** of the upstream official repository
> [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant). Since the official repository declined to
> add delete and update functionality, these features (`qdrant-delete` / `qdrant-update`) are implemented and
> published through this fork.

> The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) is an open protocol that enables
> seamless integration between LLM applications and external data sources and tools. Whether you're building an
> AI-powered IDE, enhancing a chat interface, or creating custom AI workflows, MCP provides a standardized way to
> connect LLMs with the context they need.

This repository is an example of how to create a MCP server for [Qdrant](https://qdrant.tech/), a vector search engine.

## Overview

A feature-enhanced fork of the official Model Context Protocol server for keeping, retrieving, updating and
deleting memories in the Qdrant vector search engine. It acts as a semantic memory layer on top of the Qdrant database.

## Components

### Tools

1. `qdrant-store`
   - Store some information in the Qdrant database
   - Input:
     - `information` (string): Information to store
     - `metadata` (JSON): Optional metadata to store
     - `collection_name` (string): Name of the collection to store the information in. This field is required if there are no default collection name.
                                   If there is a default collection name, this field is not enabled.
   - Returns: Confirmation message
2. `qdrant-find`
   - Retrieve relevant information from the Qdrant database
   - Input:
     - `query` (string): Query to use for searching
     - `collection_name` (string): Name of the collection to store the information in. This field is required if there are no default collection name.
                                   If there is a default collection name, this field is not enabled.
   - Returns: Information stored in the Qdrant database as separate messages. Each result includes
              the point `id` and the similarity `score`, which are the handles for `qdrant-update` / `qdrant-delete`.
3. `qdrant-update`
   - Update an existing entry in place, identified by its point ID. The content is re-embedded with the
     configured embedding model and the point keeps its ID. Nothing is changed if the point ID does not exist.
   - Input:
     - `point_id` (string): Point ID of the entry to update, as returned by `qdrant-find`
     - `information` (string): New information to store
     - `metadata` (JSON): Optional new metadata to store (replaces any previously stored metadata)
     - `collection_name` (string): Name of the collection the entry belongs to. This field is required if there
                                   are no default collection name. If there is a default collection name, this
                                   field is not enabled.
   - Returns: Confirmation message, or a non-destructive notice if the point ID was not found
4. `qdrant-delete`
   - Delete entries from the Qdrant database, identified by their point IDs. Deletion is irreversible;
     always confirm with the user before calling this tool.
   - Input:
     - `point_ids` (list of strings): Point IDs of the entries to delete, as returned by `qdrant-find`
     - `collection_name` (string): Name of the collection the entries belong to. This field is required if there
                                   are no default collection name. If there is a default collection name, this
                                   field is not enabled.
   - Returns: A message listing the deleted entries' content (for verification) and any IDs that were not found

## Environment Variables

Configuration is done via environment variables. The only command-line argument is `--transport`, used to select the [transport protocol](#transport-protocols).

> [!NOTE]
> You cannot provide both `QDRANT_URL` and `QDRANT_LOCAL_PATH` at the same time.

| Name                     | Description                                                         | Default Value                                                     |
|--------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------|
| `QDRANT_URL`             | URL of the Qdrant server                                            | None                                                              |
| `QDRANT_API_KEY`         | API key for the Qdrant server                                       | None                                                              |
| `COLLECTION_NAME`        | Name of the default collection to use.                              | None                                                              |
| `QDRANT_LOCAL_PATH`      | Path to the local Qdrant database (alternative to `QDRANT_URL`)     | None                                                              |
| `EMBEDDING_PROVIDER`     | Embedding provider to use (currently only "fastembed" is supported) | `fastembed`                                                       |
| `EMBEDDING_MODEL`        | Name of the embedding model to use                                  | `sentence-transformers/all-MiniLM-L6-v2`                          |
| `TOOL_STORE_DESCRIPTION` | Custom description for the store tool                               | See default in [`settings.py`](src/mcp_server_qdrant/settings.py) |
| `TOOL_FIND_DESCRIPTION`  | Custom description for the find tool                                | See default in [`settings.py`](src/mcp_server_qdrant/settings.py) |
| `TOOL_UPDATE_DESCRIPTION` | Custom description for the update tool                             | See default in [`settings.py`](src/mcp_server_qdrant/settings.py) |
| `TOOL_DELETE_DESCRIPTION` | Custom description for the delete tool                             | See default in [`settings.py`](src/mcp_server_qdrant/settings.py) |
| `QDRANT_SEARCH_LIMIT`    | Maximum number of results to return from search                     | `10`                                                              |
| `QDRANT_READ_ONLY`       | Enable read-only mode (disables the `qdrant-store`, `qdrant-update` and `qdrant-delete` tools) | `false` |

### FastMCP Environment Variables

Since `mcp-server-qdrant` is based on FastMCP, it also supports all the FastMCP environment variables. The most
important ones are listed below:

| Environment Variable                       | Description                                                     | Default Value |
|--------------------------------------------|-----------------------------------------------------------------|---------------|
| `FASTMCP_LOG_LEVEL`                        | Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)       | `INFO`        |
| `FASTMCP_SERVER_DEBUG`                     | Enable debug mode                                               | `false`       |
| `FASTMCP_SERVER_HOST`                      | Host address to bind the server to                              | `127.0.0.1`   |
| `FASTMCP_SERVER_PORT`                      | Port to run the server on                                       | `8000`        |
| `FASTMCP_SERVER_ON_DUPLICATE_RESOURCES`    | Behavior for duplicate resources (warn, error, replace, ignore) | `warn`        |
| `FASTMCP_SERVER_ON_DUPLICATE_TOOLS`        | Behavior for duplicate tools (warn, error, replace, ignore)     | `warn`        |
| `FASTMCP_SERVER_ON_DUPLICATE_PROMPTS`      | Behavior for duplicate prompts (warn, error, replace, ignore)   | `warn`        |
| `FASTMCP_SERVER_DEPENDENCIES`              | List of dependencies to install in the server environment       | `[]`          |

> [!NOTE]
> Server-specific settings use the `FASTMCP_SERVER_` prefix. This may change in future versions.

## Installation

### Using uvx

This fork is not published to PyPI (the `mcp-server-qdrant` name there belongs to the official
upstream project), so use `--from` to have uvx build and run it directly from this GitHub repository:

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant
```

> [!TIP]
> The first run builds from source and takes a while. To pick up the latest code later, re-run with
> `--refresh` to force a re-fetch.

#### Transport Protocols

The server supports different transport protocols that can be specified using the `--transport` flag:

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse
```

Supported transport protocols:

- `stdio` (default): Standard input/output transport, might only be used by local MCP clients
- `sse`: Server-Sent Events transport, perfect for remote clients
- `streamable-http`: Streamable HTTP transport, perfect for remote clients, more recent than SSE

The default transport is `stdio` if not specified.

When SSE transport is used, the server will listen on the specified port and wait for incoming connections. The default
port is 8000, however it can be changed using the `FASTMCP_SERVER_PORT` environment variable.

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
FASTMCP_SERVER_PORT=1234 \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse
```

### Using Docker

Images are built and published to `ghcr.io` by GitHub Actions (`.github/workflows/docker-publish.yaml`):
pushes to `master` publish the rolling `master` and `sha-*` tags, `v*` version tags publish `X.Y.Z`
and `X.Y` tags. There is no `latest` tag — deployments should pin an explicit version. The server
runs with the streamable-http transport by default:

```bash
# Run the published image
docker run -d -p 8000:8000 \
  -e QDRANT_URL="http://your-qdrant-server:6333" \
  -e EMBEDDING_MODEL="jinaai/jina-embeddings-v2-base-zh" \
  ghcr.io/sinonjzh/mcp-server-qdrant:0.9.0

# Or build it locally from source
docker build -t mcp-server-qdrant .
```

> [!TIP]
> The image already sets `FASTMCP_SERVER_HOST=0.0.0.0` and `FASTMCP_SERVER_PORT=8000`. The embedding
> model is not baked into the image: point `FASTEMBED_CACHE_PATH` to a mounted volume that holds (or
> will hold) the model. With `HF_HUB_OFFLINE=1`, the cache must already be populated.

### Manual configuration of Claude Desktop

To use this server with the Claude Desktop app, add the following configuration to the "mcpServers" section of your
`claude_desktop_config.json`:

```json
{
  "qdrant": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/SinonJZH/mcp-server-qdrant", "mcp-server-qdrant"],
    "env": {
      "QDRANT_URL": "https://xyz-example.eu-central.aws.cloud.qdrant.io:6333",
      "QDRANT_API_KEY": "your_api_key",
      "COLLECTION_NAME": "your-collection-name",
      "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
    }
  }
}
```

For local Qdrant mode:

```json
{
  "qdrant": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/SinonJZH/mcp-server-qdrant", "mcp-server-qdrant"],
    "env": {
      "QDRANT_LOCAL_PATH": "/path/to/qdrant/database",
      "COLLECTION_NAME": "your-collection-name",
      "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
    }
  }
}
```

This MCP server will automatically create a collection with the specified name if it doesn't exist.

By default, the server will use the `sentence-transformers/all-MiniLM-L6-v2` embedding model to encode memories.
For the time being, only [FastEmbed](https://qdrant.github.io/fastembed/) models are supported.

## Support for other tools

This MCP server can be used with any MCP-compatible client. For example, you can use it with
[Cursor](https://docs.cursor.com/context/model-context-protocol) and [VS Code](https://code.visualstudio.com/docs), which provide built-in support for the Model Context
Protocol.

### Using with Cursor/Windsurf

You can configure this MCP server to work as a code search tool for Cursor or Windsurf by customizing the tool
descriptions:

```bash
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="code-snippets" \
TOOL_STORE_DESCRIPTION="Store reusable code snippets for later retrieval. \
The 'information' parameter should contain a natural language description of what the code does, \
while the actual code should be included in the 'metadata' parameter as a 'code' property. \
The value of 'metadata' is a Python dictionary with strings as keys. \
Use this whenever you generate some code snippet." \
TOOL_FIND_DESCRIPTION="Search for relevant code snippets based on natural language descriptions. \
The 'query' parameter should describe what you're looking for, \
and the tool will return the most relevant code snippets. \
Use this when you need to find existing code snippets for reuse or reference." \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse # Enable SSE transport
```

In Cursor/Windsurf, you can then configure the MCP server in your settings by pointing to this running server using
SSE transport protocol. The description on how to add an MCP server to Cursor can be found in the [Cursor
documentation](https://docs.cursor.com/context/model-context-protocol#adding-an-mcp-server-to-cursor). If you are
running Cursor/Windsurf locally, you can use the following URL:

```
http://localhost:8000/sse
```

> [!TIP]
> We suggest SSE transport as a preferred way to connect Cursor/Windsurf to the MCP server, as it can support remote
> connections. That makes it easy to share the server with your team or use it in a cloud environment.

This configuration transforms the Qdrant MCP server into a specialized code search tool that can:

1. Store code snippets, documentation, and implementation details
2. Retrieve relevant code examples based on semantic search
3. Help developers find specific implementations or usage patterns

You can populate the database by storing natural language descriptions of code snippets (in the `information` parameter)
along with the actual code (in the `metadata.code` property), and then search for them using natural language queries
that describe what you're looking for.

> [!NOTE]
> The tool descriptions provided above are examples and may need to be customized for your specific use case. Consider
> adjusting the descriptions to better match your team's workflow and the specific types of code snippets you want to
> store and retrieve.

**If you have successfully installed the `mcp-server-qdrant`, but still can't get it to work with Cursor, please
consider creating the [Cursor rules](https://docs.cursor.com/context/rules-for-ai) so the MCP tools are always used when
the agent produces a new code snippet.** You can restrict the rules to only work for certain file types, to avoid using
the MCP server for the documentation or other types of content.

### Using with Claude Code

You can enhance Claude Code's capabilities by connecting it to this MCP server, enabling semantic search over your
existing codebase.

#### Setting up mcp-server-qdrant

1. Add the MCP server to Claude Code:

    ```shell
    # Add mcp-server-qdrant configured for code search
    claude mcp add code-search \
    -e QDRANT_URL="http://localhost:6333" \
    -e COLLECTION_NAME="code-repository" \
    -e EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
    -e TOOL_STORE_DESCRIPTION="Store code snippets with descriptions. The 'information' parameter should contain a natural language description of what the code does, while the actual code should be included in the 'metadata' parameter as a 'code' property." \
    -e TOOL_FIND_DESCRIPTION="Search for relevant code snippets using natural language. The 'query' parameter should describe the functionality you're looking for." \
    -- uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant
    ```

2. Verify the server was added:

    ```shell
    claude mcp list
    ```

#### Using Semantic Code Search in Claude Code

Tool descriptions, specified in `TOOL_STORE_DESCRIPTION` and `TOOL_FIND_DESCRIPTION`, guide Claude Code on how to use
the MCP server. The ones provided above are examples and may need to be customized for your specific use case. However,
Claude Code should be already able to:

1. Use the `qdrant-store` tool to store code snippets with descriptions.
2. Use the `qdrant-find` tool to search for relevant code snippets using natural language.

### Run MCP server in Development Mode

The MCP server can be run in development mode using the `mcp dev` command. This will start the server and open the MCP
inspector in your browser.

```shell
COLLECTION_NAME=mcp-dev fastmcp dev src/mcp_server_qdrant/server.py
```

### Using with VS Code

For one-click installation, click one of the install buttons below:

[![Install with UVX in VS Code](https://img.shields.io/badge/VS_Code-UVX-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2FSinonJZH%2Fmcp-server-qdrant%22%2C%22mcp-server-qdrant%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D) [![Install with UVX in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-UVX-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2FSinonJZH%2Fmcp-server-qdrant%22%2C%22mcp-server-qdrant%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D&quality=insiders)

[![Install with Docker in VS Code](https://img.shields.io/badge/VS_Code-Docker-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-e%22%2C%22QDRANT_URL%22%2C%22-e%22%2C%22QDRANT_API_KEY%22%2C%22-e%22%2C%22COLLECTION_NAME%22%2C%22ghcr.io%2Fsinonjzh%2Fmcp-server-qdrant%3A0.9.0%22%2C%22mcp-server-qdrant%22%2C%22--transport%22%2C%22stdio%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D) [![Install with Docker in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Docker-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-e%22%2C%22QDRANT_URL%22%2C%22-e%22%2C%22QDRANT_API_KEY%22%2C%22-e%22%2C%22COLLECTION_NAME%22%2C%22ghcr.io%2Fsinonjzh%2Fmcp-server-qdrant%3A0.9.0%22%2C%22mcp-server-qdrant%22%2C%22--transport%22%2C%22stdio%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D&quality=insiders)

#### Manual Installation

Add the following JSON block to your User Settings (JSON) file in VS Code. You can do this by pressing `Ctrl + Shift + P` and typing `Preferences: Open User Settings (JSON)`.

```json
{
  "mcp": {
    "inputs": [
      {
        "type": "promptString",
        "id": "qdrantUrl",
        "description": "Qdrant URL"
      },
      {
        "type": "promptString",
        "id": "qdrantApiKey",
        "description": "Qdrant API Key",
        "password": true
      },
      {
        "type": "promptString",
        "id": "collectionName",
        "description": "Collection Name"
      }
    ],
    "servers": {
      "qdrant": {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/SinonJZH/mcp-server-qdrant", "mcp-server-qdrant"],
        "env": {
          "QDRANT_URL": "${input:qdrantUrl}",
          "QDRANT_API_KEY": "${input:qdrantApiKey}",
          "COLLECTION_NAME": "${input:collectionName}"
        }
      }
    }
  }
}
```

Or if you prefer using Docker, add this configuration instead:

```json
{
  "mcp": {
    "inputs": [
      {
        "type": "promptString",
        "id": "qdrantUrl",
        "description": "Qdrant URL"
      },
      {
        "type": "promptString",
        "id": "qdrantApiKey",
        "description": "Qdrant API Key",
        "password": true
      },
      {
        "type": "promptString",
        "id": "collectionName",
        "description": "Collection Name"
      }
    ],
    "servers": {
      "qdrant": {
        "command": "docker",
        "args": [
          "run",
          "-i",
          "--rm",
          "-e", "QDRANT_URL",
          "-e", "QDRANT_API_KEY",
          "-e", "COLLECTION_NAME",
          "ghcr.io/sinonjzh/mcp-server-qdrant:0.9.0",
          "mcp-server-qdrant",
          "--transport", "stdio"
        ],
        "env": {
          "QDRANT_URL": "${input:qdrantUrl}",
          "QDRANT_API_KEY": "${input:qdrantApiKey}",
          "COLLECTION_NAME": "${input:collectionName}"
        }
      }
    }
  }
}
```

> [!NOTE]
> The published image starts with the streamable-http transport, while VS Code communicates with MCP
> servers over stdio. Arguments after the image name in `docker run` fully replace the image's `CMD`,
> so the configuration spells out the complete command `mcp-server-qdrant --transport stdio` to switch
> the transport. Pin the image tag to a published version as needed (e.g. `0.9` / `0.9.0`,
> see [Using Docker](#using-docker)).

Alternatively, you can create a `.vscode/mcp.json` file in your workspace with the following content:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "qdrantUrl",
      "description": "Qdrant URL"
    },
    {
      "type": "promptString",
      "id": "qdrantApiKey",
      "description": "Qdrant API Key",
      "password": true
    },
    {
      "type": "promptString",
      "id": "collectionName",
      "description": "Collection Name"
    }
  ],
  "servers": {
    "qdrant": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/SinonJZH/mcp-server-qdrant", "mcp-server-qdrant"],
      "env": {
        "QDRANT_URL": "${input:qdrantUrl}",
        "QDRANT_API_KEY": "${input:qdrantApiKey}",
        "COLLECTION_NAME": "${input:collectionName}"
      }
    }
  }
}
```

For workspace configuration with Docker, use this in `.vscode/mcp.json`:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "qdrantUrl",
      "description": "Qdrant URL"
    },
    {
      "type": "promptString",
      "id": "qdrantApiKey",
      "description": "Qdrant API Key",
      "password": true
    },
    {
      "type": "promptString",
      "id": "collectionName",
      "description": "Collection Name"
    }
  ],
  "servers": {
    "qdrant": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "QDRANT_URL",
        "-e", "QDRANT_API_KEY",
        "-e", "COLLECTION_NAME",
        "ghcr.io/sinonjzh/mcp-server-qdrant:0.9.0",
        "mcp-server-qdrant",
        "--transport", "stdio"
      ],
      "env": {
        "QDRANT_URL": "${input:qdrantUrl}",
        "QDRANT_API_KEY": "${input:qdrantApiKey}",
        "COLLECTION_NAME": "${input:collectionName}"
      }
    }
  }
}
```

## Client plugin bundles

The repository ships two directories that package this server as a plugin for specific
clients, so no hand-written JSON configuration is needed.

### Kiro Power (`kiro-power/`)

[Kiro](https://kiro.dev/) is AWS's AI IDE; Powers are its plugin mechanism (following the
open [Agent Plugins specification](https://agent-plugins.org/): a `plugin.json` manifest,
optional skills, and an optional `mcp.json`). The `kiro-power/` directory packages this
server as a Power named `qdrant`:

- `mcp.json` — starts the server via uvx from this GitHub repository (stdio); it expects
  the `QDRANT_URL` / `QDRANT_API_KEY` / `COLLECTION_NAME` / `EMBEDDING_MODEL`
  environment variables;
- `skills/setup/` — a post-install troubleshooting skill covering uvx not being reachable,
  missing or unapproved environment variables, `Failed to connect`, and similar issues.

Install it with one click from the Kiro Powers marketplace or from a GitHub repository;
see the [Kiro Powers docs](https://kiro.dev/docs/powers/).

### DSH plugin (`dsh-plugin/`)

[DSH](https://github.com/deepseek-ai/deepseek-harness) (DeepSeek Harness) users can use
`dsh-plugin/`: a single `cordis.patch.yml` that inserts one `@deepseek-ai/dsh-mcp-client`
line (stdio + uvx) into a profile. It works out of the box against a local Qdrant
(`http://localhost:6333`, collection `memories`); point it at a remote instance via the
`QDRANT_URL` / `QDRANT_API_KEY` environment variables. After activation the tools are
named `mcp__qdrant__qdrant-store` / `qdrant-find` / `qdrant-update` / `qdrant-delete`.

Install by entering the absolute path of `dsh-plugin/` in the DSH plugin page, or run
`dsh plugin --profile <profile> add /path/to/mcp-server-qdrant/dsh-plugin`. See
[`dsh-plugin/README.md`](dsh-plugin/README.md) for details.

## Contributing

If you have suggestions for how mcp-server-qdrant could be improved, or want to report a bug, open an issue!
We'd love all and any contributions.

### Testing `mcp-server-qdrant` locally

The [MCP inspector](https://github.com/modelcontextprotocol/inspector) is a developer tool for testing and debugging MCP
servers. It runs both a client UI (default port 5173) and an MCP proxy server (default port 3000). Open the client UI in
your browser to use the inspector.

```shell
QDRANT_URL=":memory:" COLLECTION_NAME="test" \
fastmcp dev src/mcp_server_qdrant/server.py
```

Once started, open your browser to http://localhost:5173 to access the inspector interface.

## License

This MCP server is licensed under the Apache License 2.0. This means you are free to use, modify, and distribute the
software, subject to the terms and conditions of the Apache License 2.0. For more details, please see the LICENSE file
in the project repository.

## Privacy and support

- [Privacy Policy](https://qdrant.tech/legal/privacy-policy/)
- [Support](https://github.com/qdrant/mcp-server-qdrant/issues)
