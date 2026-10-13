# @sinonjzh/mcp-server-qdrant-dsh

把本仓库的 mcp-server-qdrant 挂进 [DSH](https://deepseek.ai)（DeepSeek Harness）的**配置专用插件**：只有一份
`cordis.patch.yml`，向 profile 插入一行 `@deepseek-ai/dsh-mcp-client`（stdio 传输），用
uvx 从本 GitHub 仓库直接构建并启动服务器。

激活后工具名形如：

- `mcp__qdrant__qdrant-store` — 存入记忆
- `mcp__qdrant__qdrant-find` — 语义检索
- `mcp__qdrant__qdrant-update` — 按 point ID 原地更新
- `mcp__qdrant__qdrant-delete` — 按 point ID 删除

## 前置条件

- `uvx`（[uv](https://docs.astral.sh/uv/)）在 DSH 进程可见的 PATH 上；
- 一个可连的 Qdrant 实例（本地 `docker run -p 6333:6333 qdrant/qdrant`，或远端 URL）。

## 安装

两种方式选一：

**A. Web 界面** — 侧栏 **插件** → **添加插件** → 填本目录的绝对路径
（`…/mcp-server-qdrant/dsh-plugin`）→ 安装 → **立即启用**。

**B. CLI** — `dsh plugin --profile <profile> add /path/to/mcp-server-qdrant/dsh-plugin`。

## 配置

含默认值，通常零配置即可用（连 `http://localhost:6333` 的本地 Qdrant，集合名 `memories`）。
想改行为时，**优先用环境变量**（启动 DSH 前 export，密钥不落盘），也可以直接改
`cordis.patch.yml`：

| 环境变量         | 默认值                                  | 说明                     |
|------------------|-----------------------------------------|--------------------------|
| `QDRANT_URL`     | `http://localhost:6333`                 | Qdrant 服务器地址        |
| `QDRANT_API_KEY` | 空                                      | Qdrant Cloud / 带鉴权时填 |
| `COLLECTION_NAME`| `memories`                              | 默认集合名               |

- 改 `serverName`（现为 `qdrant`）会改变工具名以及权限规则/历史里的引用，改前想清楚。
- Qdrant 本身连不上不影响激活：工具照样注册，只在真正调用时报错。
- 服务器连不上（DSH 日志出现 `Failed to connect` / spawn 失败）时，先在**启动 DSH 的同一环境**里
  执行 `command -v uvx && uvx --version`，确认 uvx 可达——大多数连不上都是 PATH 问题。

## 验证

```sh
dsh --profile <profile> --dump-config | grep -A12 'mcp-qdrant'   # 该行已插入，env 仍是 !!js 表达式
```

安装后**新开一个会话**，工具表里应出现 `mcp__qdrant__*`。

## 首次激活较慢

首次激活时 uvx 要从 GitHub 克隆并构建本项目，耗时可能超过 mcp-client 的重试预算
（默认连续 10 次失败后退避停止）。这不影响 profile 组合（`failOnStartupError` 保持
默认 `false`）；遇到时重载配置或新开会话即可——uvx 已有本地缓存，第二次连接很快。
也可以先在终端手动跑一次预热缓存：

```sh
uvx --from git+https://github.com/SinonJZH/mcp-server-qdrant mcp-server-qdrant --help
```

## 卸载

插件页对 `@sinonjzh/mcp-server-qdrant-dsh` 执行卸载即可（会从 profile 的
`package.json` 与 `node_modules` 移除，patch 段随之失效）。
