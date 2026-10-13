# mcp-server-qdrant：Qdrant MCP 服务器

中文 | [English](README.en.md)

> [!IMPORTANT]
> 本仓库是对上游官方仓库 [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant)
> fork 后实现的**功能增强版**。由于官方仓库拒绝加入删除和修改功能，
> 相关功能（`qdrant-delete` / `qdrant-update`）通过本 fork 仓库实现并发布。

> [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction)
> 是一个开放协议，用于在 LLM 应用与外部数据源、工具之间实现无缝集成。无论你是在构建
> AI 驱动的 IDE、增强聊天界面，还是创建自定义 AI 工作流，MCP 都提供了一种标准化的方式，
> 将 LLM 与其所需的上下文连接起来。

本仓库展示了如何为向量搜索引擎 [Qdrant](https://qdrant.tech/) 创建一个 MCP 服务器。

## 概述

基于官方 Model Context Protocol 服务器的功能增强版，用于在 Qdrant 向量搜索引擎中保存、检索、更新和删除记忆。
它在 Qdrant 数据库之上充当一个语义记忆层。

## 组件

### 工具

1. `qdrant-store`
   - 向 Qdrant 数据库中存储信息
   - 输入：
     - `information` (string)：要存储的信息
     - `metadata` (JSON)：可选的元数据
     - `collection_name` (string)：存储信息的目标集合名称。未设置默认集合名称时此字段必填；
                                   已设置默认集合名称时此字段不可用。
   - 返回：确认消息
2. `qdrant-find`
   - 从 Qdrant 数据库中检索相关信息
   - 输入：
     - `query` (string)：用于搜索的查询语句
     - `collection_name` (string)：存储信息的目标集合名称。未设置默认集合名称时此字段必填；
                                   已设置默认集合名称时此字段不可用。
   - 返回：以多条独立消息的形式返回存储在 Qdrant 数据库中的信息。每条结果都包含 point 的
            `id` 和相似度 `score`，它们是调用 `qdrant-update` / `qdrant-delete` 的操作句柄。
3. `qdrant-update`
   - 按 point ID 原地更新已有条目。内容会使用所配置的 embedding 模型重新嵌入，
     且 point 保持其 ID 不变。若 point ID 不存在，则不做任何更改。
   - 输入：
     - `point_id` (string)：要更新的条目的 point ID，来自 `qdrant-find` 的返回结果
     - `information` (string)：要存储的新信息
     - `metadata` (JSON)：可选的新元数据（会替换之前存储的元数据）
     - `collection_name` (string)：条目所属集合的名称。未设置默认集合名称时此字段必填；
                                   已设置默认集合名称时此字段不可用。
   - 返回：确认消息；若 point ID 未找到，则返回一条非破坏性的提示
4. `qdrant-delete`
   - 按 point ID 从 Qdrant 数据库中删除条目。删除操作不可逆；
     调用此工具前务必先征得用户确认。
   - 输入：
     - `point_ids` (string 列表)：要删除条目的 point ID，来自 `qdrant-find` 的返回结果
     - `collection_name` (string)：条目所属集合的名称。未设置默认集合名称时此字段必填；
                                   已设置默认集合名称时此字段不可用。
   - 返回：一条消息，列出被删条目的内容（供核对）以及未找到的 ID

## 环境变量

配置通过环境变量完成。唯一的命令行参数是 `--transport`，用于选择[传输协议](#传输协议)。

> [!NOTE]
> `QDRANT_URL` 与 `QDRANT_LOCAL_PATH` 不能同时提供。

| 名称                      | 描述                                                                   | 默认值                                                            |
|---------------------------|------------------------------------------------------------------------|-------------------------------------------------------------------|
| `QDRANT_URL`              | Qdrant 服务器的 URL                                                    | 无                                                                |
| `QDRANT_API_KEY`          | Qdrant 服务器的 API 密钥                                               | 无                                                                |
| `COLLECTION_NAME`         | 默认集合的名称。                                                        | 无                                                                |
| `QDRANT_LOCAL_PATH`       | 本地 Qdrant 数据库路径（`QDRANT_URL` 的替代方案）                       | 无                                                                |
| `EMBEDDING_PROVIDER`      | 要使用的 embedding 提供方（目前仅支持 "fastembed"）                     | `fastembed`                                                       |
| `EMBEDDING_MODEL`         | 要使用的 embedding 模型名称                                             | `sentence-transformers/all-MiniLM-L6-v2`                          |
| `TOOL_STORE_DESCRIPTION`  | store 工具的自定义描述                                                  | 默认值见 [`settings.py`](src/mcp_server_qdrant/settings.py)       |
| `TOOL_FIND_DESCRIPTION`   | find 工具的自定义描述                                                   | 默认值见 [`settings.py`](src/mcp_server_qdrant/settings.py)       |
| `TOOL_UPDATE_DESCRIPTION` | update 工具的自定义描述                                                 | 默认值见 [`settings.py`](src/mcp_server_qdrant/settings.py)       |
| `TOOL_DELETE_DESCRIPTION` | delete 工具的自定义描述                                                 | 默认值见 [`settings.py`](src/mcp_server_qdrant/settings.py)       |
| `QDRANT_SEARCH_LIMIT`     | 搜索返回的最大结果数                                                    | `10`                                                              |
| `QDRANT_READ_ONLY`        | 启用只读模式（禁用 `qdrant-store`、`qdrant-update` 和 `qdrant-delete` 工具） | `false`                                                       |

### FastMCP 环境变量

由于 `mcp-server-qdrant` 基于 FastMCP 构建，它同样支持所有 FastMCP
环境变量。其中最重要的几个如下所列：

| 环境变量                                   | 描述                                                             | 默认值        |
|--------------------------------------------|------------------------------------------------------------------|---------------|
| `FASTMCP_LOG_LEVEL`                        | 设置日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）            | `INFO`        |
| `FASTMCP_SERVER_DEBUG`                     | 启用调试模式                                                     | `false`       |
| `FASTMCP_SERVER_HOST`                      | 服务器绑定的主机地址                                             | `127.0.0.1`   |
| `FASTMCP_SERVER_PORT`                      | 服务器监听的端口                                                 | `8000`        |
| `FASTMCP_SERVER_ON_DUPLICATE_RESOURCES`    | 资源重复时的处理方式（warn、error、replace、ignore）             | `warn`        |
| `FASTMCP_SERVER_ON_DUPLICATE_TOOLS`        | 工具重复时的处理方式（warn、error、replace、ignore）             | `warn`        |
| `FASTMCP_SERVER_ON_DUPLICATE_PROMPTS`      | 提示重复时的处理方式（warn、error、replace、ignore）             | `warn`        |
| `FASTMCP_SERVER_DEPENDENCIES`              | 要在服务器环境中安装的依赖列表                                   | `[]`          |

> [!NOTE]
> 服务器专属配置项使用 `FASTMCP_SERVER_` 前缀。未来版本中这可能会变化。

## 安装

### 使用 uvx

本 fork 未发布到 PyPI（`mcp-server-qdrant` 这个名字已被上游官方项目占用），因此需要通过
`--from` 让 uvx 直接从 GitHub 拉取本仓库构建运行：

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant
```

> [!TIP]
> 首次运行会从源码构建，耗时会长一些。之后若想更新到最新代码，重新运行时加上
> `--refresh` 参数即可强制重新拉取。

#### 传输协议

服务器支持多种传输协议，可通过 `--transport` 标志指定：

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse
```

支持的传输协议：

- `stdio`（默认）：标准输入/输出传输，通常只能被本地 MCP 客户端使用
- `sse`：Server-Sent Events 传输，非常适合远程客户端
- `streamable-http`：Streamable HTTP 传输，适合远程客户端，比 SSE 更新

未指定时默认使用 `stdio`。

使用 SSE 传输时，服务器会在指定端口上监听并等待连接。默认端口为 8000，
可通过 `FASTMCP_SERVER_PORT` 环境变量修改。

```shell
QDRANT_URL="http://localhost:6333" \
COLLECTION_NAME="my-collection" \
FASTMCP_SERVER_PORT=1234 \
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse
```

### 使用 Docker

镜像由 GitHub Actions（`.github/workflows/docker-publish.yaml`）构建并发布到
`ghcr.io`：推送到 `master` 会发布滚动的 `master` 和 `sha-*` 标签，`v*`
版本标签会发布 `X.Y.Z` 和 `X.Y` 标签。不提供 `latest` 标签——部署时应固定使用明确的版本。
服务器默认以 streamable-http 传输运行：

```bash
# 运行已发布的镜像
docker run -d -p 8000:8000 \
  -e QDRANT_URL="http://your-qdrant-server:6333" \
  -e EMBEDDING_MODEL="jinaai/jina-embeddings-v2-base-zh" \
  ghcr.io/sinonjzh/mcp-server-qdrant:0.9.0

# 或者从源码本地构建
docker build -t mcp-server-qdrant .
```

> [!TIP]
> 镜像内已预设 `FASTMCP_SERVER_HOST=0.0.0.0` 和 `FASTMCP_SERVER_PORT=8000`。embedding
> 模型不会打包进镜像：请将 `FASTEMBED_CACHE_PATH` 指向一个挂载卷，其中存放（或即将存放）模型。
> 若设置 `HF_HUB_OFFLINE=1`，则缓存中必须已存在模型。

### 手动配置 Claude Desktop

要在 Claude Desktop 应用中使用本服务器，请在 `claude_desktop_config.json` 的
"mcpServers" 部分添加以下配置：

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

本地 Qdrant 模式的配置如下：

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

如果指定的集合不存在，本 MCP 服务器会自动创建它。

默认情况下，服务器使用 `sentence-transformers/all-MiniLM-L6-v2` embedding 模型对记忆进行编码。
目前仅支持 [FastEmbed](https://qdrant.github.io/fastembed/) 模型。

## 与其他工具配合使用

本 MCP 服务器可用于任何兼容 MCP 的客户端。例如，可以在原生支持 Model Context
Protocol 的 [Cursor](https://docs.cursor.com/context/model-context-protocol) 和
[VS Code](https://code.visualstudio.com/docs) 中使用它。

### 在 Cursor/Windsurf 中使用

通过自定义工具描述，可以将本 MCP 服务器配置为 Cursor 或 Windsurf 的代码搜索工具：

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
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --transport sse # 启用 SSE 传输
```

然后在 Cursor/Windsurf 的设置中配置 MCP 服务器，通过 SSE 传输协议指向这个运行中的服务器。
关于如何向 Cursor 添加 MCP 服务器，请参阅 [Cursor 文档](https://docs.cursor.com/context/model-context-protocol#adding-an-mcp-server-to-cursor)。
如果在本地运行 Cursor/Windsurf，可以使用以下 URL：

```
http://localhost:8000/sse
```

> [!TIP]
> 建议优先使用 SSE 传输协议将 Cursor/Windsurf 连接到 MCP 服务器，因为它支持远程连接，
> 方便与团队共享服务器或在云环境中使用。

通过这样的配置，Qdrant MCP 服务器就变成了一个专门的代码搜索工具，能够：

1. 存储代码片段、文档和实现细节
2. 基于语义搜索检索相关的代码示例
3. 帮助开发者找到特定的实现或用法模式

存入数据时，可以把代码片段的自然语言描述（放在 `information` 参数中）连同实际代码
（放在 `metadata.code` 属性中）一起存储，之后便可以用描述目标内容的自然语言查询来搜索它们。

> [!NOTE]
> 上面的工具描述只是示例，可能需要根据你的具体用例进行定制。建议根据团队的工作流程以及
> 想要存储和检索的代码片段类型来调整描述。

**如果你已成功安装 `mcp-server-qdrant`，但仍无法在 Cursor 中正常使用，请考虑创建
[Cursor rules](https://docs.cursor.com/context/rules-for-ai)，让 agent
在生成新代码片段时始终使用 MCP 工具。** 你可以将规则限定为只对特定文件类型生效，
避免在文档或其他类型的内容上调用 MCP 服务器。

### 在 Claude Code 中使用

将本 MCP 服务器连接到 Claude Code，可以对其现有代码库进行语义搜索，从而增强 Claude Code 的能力。

#### 配置 mcp-server-qdrant

1. 将 MCP 服务器添加到 Claude Code：

    ```shell
    # 添加针对代码搜索配置的 mcp-server-qdrant
    claude mcp add code-search \
    -e QDRANT_URL="http://localhost:6333" \
    -e COLLECTION_NAME="code-repository" \
    -e EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
    -e TOOL_STORE_DESCRIPTION="Store code snippets with descriptions. The 'information' parameter should contain a natural language description of what the code does, while the actual code should be included in the 'metadata' parameter as a 'code' property." \
    -e TOOL_FIND_DESCRIPTION="Search for relevant code snippets using natural language. The 'query' parameter should describe the functionality you're looking for." \
    -- uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant
    ```

2. 验证服务器已添加：

    ```shell
    claude mcp list
    ```

#### 在 Claude Code 中使用语义代码搜索

在 `TOOL_STORE_DESCRIPTION` 和 `TOOL_FIND_DESCRIPTION` 中指定的工具描述会引导
Claude Code 如何使用 MCP 服务器。上面提供的描述只是示例，可能需要针对你的具体用例进行定制。
不过，Claude Code 通常已经能够：

1. 使用 `qdrant-store` 工具存储带描述的代码片段。
2. 使用 `qdrant-find` 工具用自然语言搜索相关的代码片段。

### 以开发模式运行 MCP 服务器

可以使用 `mcp dev` 命令以开发模式运行 MCP 服务器。该命令会启动服务器并在浏览器中打开
MCP inspector。

```shell
COLLECTION_NAME=mcp-dev fastmcp dev src/mcp_server_qdrant/server.py
```

### 在 VS Code 中使用

如需一键安装，请点击下方安装按钮之一：

[![Install with UVX in VS Code](https://img.shields.io/badge/VS_Code-UVX-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2FSinonJZH%2Fmcp-server-qdrant%22%2C%22mcp-server-qdrant%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D) [![Install with UVX in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-UVX-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2FSinonJZH%2Fmcp-server-qdrant%22%2C%22mcp-server-qdrant%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D&quality=insiders)

[![Install with Docker in VS Code](https://img.shields.io/badge/VS_Code-Docker-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-e%22%2C%22QDRANT_URL%22%2C%22-e%22%2C%22QDRANT_API_KEY%22%2C%22-e%22%2C%22COLLECTION_NAME%22%2C%22ghcr.io%2Fsinonjzh%2Fmcp-server-qdrant%3A0.9.0%22%2C%22mcp-server-qdrant%22%2C%22--transport%22%2C%22stdio%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D) [![Install with Docker in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Docker-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=qdrant&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-e%22%2C%22QDRANT_URL%22%2C%22-e%22%2C%22QDRANT_API_KEY%22%2C%22-e%22%2C%22COLLECTION_NAME%22%2C%22ghcr.io%2Fsinonjzh%2Fmcp-server-qdrant%3A0.9.0%22%2C%22mcp-server-qdrant%22%2C%22--transport%22%2C%22stdio%22%5D%2C%22env%22%3A%7B%22QDRANT_URL%22%3A%22%24%7Binput%3AqdrantUrl%7D%22%2C%22QDRANT_API_KEY%22%3A%22%24%7Binput%3AqdrantApiKey%7D%22%2C%22COLLECTION_NAME%22%3A%22%24%7Binput%3AcollectionName%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantUrl%22%2C%22description%22%3A%22Qdrant+URL%22%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22qdrantApiKey%22%2C%22description%22%3A%22Qdrant+API+Key%22%2C%22password%22%3Atrue%7D%2C%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22collectionName%22%2C%22description%22%3A%22Collection+Name%22%7D%5D&quality=insiders)

#### 手动安装

将以下 JSON 块添加到 VS Code 的用户设置（JSON）文件中。可以按 `Ctrl + Shift + P`
并输入 `Preferences: Open User Settings (JSON)` 来打开该文件。

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

如果你更习惯使用 Docker，请改为添加以下配置：

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
> 镜像默认以 streamable-http 传输启动，而 VS Code 通过 stdio 与 MCP 服务器通信。
> `docker run` 中跟在镜像名之后的参数会整体替换镜像的 `CMD`，因此配置在镜像名后写出了完整命令
> `mcp-server-qdrant --transport stdio` 来切换传输方式。镜像标签请固定为实际发布的版本
> （如 `0.9` / `0.9.0`，见[使用 Docker](#使用-docker)）。

或者，也可以在工作区中创建 `.vscode/mcp.json` 文件，内容如下：

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

如果要在工作区配置中使用 Docker，请在 `.vscode/mcp.json` 中使用以下内容：

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

## 客户端插件包

仓库内置了两个目录，把本服务器打包成特定客户端的插件，安装后无需手写 JSON 配置。

### Kiro Power（`kiro-power/`）

[Kiro](https://kiro.dev/) 是 AWS 推出的 AI IDE，Power 是它的插件机制（遵循开放的
[Agent Plugins 规范](https://agent-plugins.org/)：`plugin.json` 清单 + 可选 skills +
可选 `mcp.json`）。`kiro-power/` 目录把本服务器打包为名为 `qdrant` 的 Power：

- `mcp.json` — 用 uvx 从本 GitHub 仓库启动服务器（stdio），需要
  `QDRANT_URL` / `QDRANT_API_KEY` / `COLLECTION_NAME` / `EMBEDDING_MODEL`
  四个环境变量；
- `skills/setup/` — 安装后的排障引导 skill，覆盖 uvx 不可达、环境变量缺失或未在
  Kiro 中批准、`Failed to connect` 等常见问题。

从 Kiro Powers 市场或 GitHub 仓库一键安装即可，详见
[Kiro Powers 文档](https://kiro.dev/docs/powers/)。

### DSH 插件（`dsh-plugin/`）

[DSH](https://github.com/deepseek-ai/deepseek-harness)（DeepSeek Harness）用户可以使用
`dsh-plugin/`：一份 `cordis.patch.yml` 向 profile 插入一行
`@deepseek-ai/dsh-mcp-client`（stdio + uvx）。零配置即可连本地 Qdrant
（默认 `http://localhost:6333`、集合 `memories`）；连远端实例时通过
`QDRANT_URL` / `QDRANT_API_KEY` 环境变量覆盖。激活后工具名为
`mcp__qdrant__qdrant-store` / `qdrant-find` / `qdrant-update` / `qdrant-delete`。

安装：在 DSH 插件页填入 `dsh-plugin/` 的绝对路径，或执行
`dsh plugin --profile <profile> add /path/to/mcp-server-qdrant/dsh-plugin`。
更多细节见 [`dsh-plugin/README.md`](dsh-plugin/README.md)。

## 参与贡献

如果你对如何改进 mcp-server-qdrant 有建议，或者想报告 bug，欢迎提交 issue！
我们欢迎任何形式的贡献。

### 本地测试 `mcp-server-qdrant`

[MCP inspector](https://github.com/modelcontextprotocol/inspector)
是一款用于测试和调试 MCP 服务器的开发者工具。它会同时运行一个客户端 UI（默认端口 5173）
和一个 MCP 代理服务器（默认端口 3000）。在浏览器中打开客户端 UI 即可使用 inspector。

```shell
QDRANT_URL=":memory:" COLLECTION_NAME="test" \
fastmcp dev src/mcp_server_qdrant/server.py
```

启动后，在浏览器中访问 http://localhost:5173 即可进入 inspector 界面。

## 许可证

本 MCP 服务器基于 Apache License 2.0 许可证授权。这意味着你可以在遵守 Apache License 2.0
条款和条件的前提下自由使用、修改和分发本软件。更多详情请参阅项目仓库中的 LICENSE 文件。

## 隐私与支持

- [隐私政策](https://qdrant.tech/legal/privacy-policy/)
- [技术支持](https://github.com/qdrant/mcp-server-qdrant/issues)
