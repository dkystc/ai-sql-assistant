# AI SQL Assistant

一个基于 **FastAPI + DeepSeek** 的迷你 AI 数据工程助手,支持 SQL 生成、解释、优化和多轮对话。

## 项目背景

这个项目是我在研究开源数据平台 [DataNote](https://github.com/datanote1018/datanote) 的 AI 集成源码后,用 Python 重新实现的精简版。功能对标 DataNote 的 AI 助手模块,但做了三个关键增强:

- ✅ **流式输出** (SSE) - 原版是一次性返回,体验迟钝
- ✅ **多轮对话记忆** - 原版每次问答都是孤立的
- ✅ **Provider 抽象** - 原版是硬编码分支,扩展新模型要改核心逻辑

代码量对比:Java 版 537 行 → Python 版 **350 行**。

## 功能

| 模式 | 说明 |
|---|---|
| 对话 | 多轮对话,AI 记得上下文 |
| SQL 解释 | 粘贴 SQL,获得详细解读 |
| SQL 优化 | 粘贴 SQL,获得性能优化建议 |
| NL→SQL | 用自然语言描述需求,生成 SQL |

## 技术栈

- **后端**: FastAPI 0.136 + OpenAI SDK 2.x + Pydantic v2
- **前端**: 单 HTML 文件 + Tailwind CSS (CDN) + Vanilla JS + marked.js + highlight.js
- **AI 模型**: DeepSeek Chat (保留 Anthropic Provider 扩展接口)
- **会话存储**: 内存字典 + 线程锁 (单进程方案)

## 项目结构

\`\`\`
ai-sql-assistant/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── api/ai.py               # 路由层 (13 个端点)
│   ├── core/config.py          # Pydantic Settings 配置
│   ├── models/schemas.py       # 请求/响应 DTO
│   └── services/
│       ├── ai_service.py       # 业务逻辑 + SYSTEM_PROMPT
│       ├── llm_provider.py     # LLM 抽象层
│       └── session_manager.py  # 会话管理
├── static/index.html           # 单文件前端
├── .env                        # 配置 (不入库)
├── .env.example
└── README.md
\`\`\`

## 快速启动

### 1. 准备环境

需要 Python 3.10+,WSL2/Linux/macOS 均可。

\`\`\`bash
git clone <this-repo>
cd ai-sql-assistant

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install fastapi "uvicorn[standard]" openai pydantic pydantic-settings python-dotenv
\`\`\`

### 2. 配置 API Key

\`\`\`bash
cp .env.example .env
# 编辑 .env,填入你的 DeepSeek API Key
# 申请地址: https://platform.deepseek.com
\`\`\`

### 3. 启动

\`\`\`bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
\`\`\`

访问:
- 前端: http://localhost:8100
- API 文档: http://localhost:8100/docs

## API 端点

### 核心对话端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/ai/chat | 对话(非流式) |
| POST | /api/ai/chat/stream | 对话(SSE 流式) |
| POST | /api/ai/explain | SQL 解释 |
| POST | /api/ai/optimize | SQL 优化 |
| POST | /api/ai/nl2sql | NL→SQL |

对应流式版本都在 `/xxx/stream`。

### 会话管理

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/ai/sessions | 创建会话 |
| GET | /api/ai/sessions | 列出所有会话 |
| GET | /api/ai/sessions/{id} | 获取会话详情 |
| DELETE | /api/ai/sessions/{id} | 删除会话 |

## 设计亮点

### 1. LLMProvider 抽象

扩展新模型只需添加一个子类,无需改业务代码:

\`\`\`python
class NewProvider(LLMProvider):
    def chat(self, messages, max_tokens=4096) -> str: ...
    def chat_stream(self, messages, max_tokens=4096) -> Iterator[str]: ...
\`\`\`

### 2. 单 SYSTEM_PROMPT 多模式复用

4 种模式共享同一 system prompt,只通过拼接不同的 user message 实现模式切换。

### 3. 流式累积 + 会话写回

流式对话的难点是:**边 yield 给前端,边累积完整回复,流结束后一次性写入会话历史**。这样用户体验到打字机效果,同时保证对话连续性。

## 已知限制

- 会话仅存在内存中,服务重启丢失。生产环境建议改用 Redis 或数据库
- 无用户隔离,所有会话全局可见(单机个人使用不影响)
- 无长期记忆/跨会话上下文(可通过 RAG + 向量数据库扩展)
- Anthropic Provider 留了接口但未实现

## License

MIT
