# 飞书CLI笔记智能体（NoteAgent）优化报告

> 优化时间：2026-05-29
> 优化范围：核心稳定性、架构解耦、会话管理、安全防护

---

## 一、核心稳定性修复（方向一）

### 1.1 修复错误处理路径

**问题描述：** `LarkCLI.execute_command` 中 `handle_feishu_error()` 内部直接 `raise` 异常，导致下方的 `return CLIResult(success=False)` 永远不可达。工具层的 `if not result.success` 防御逻辑形同虚设，所有飞书CLI错误都以未捕获异常的形式暴露到上层。

**技术方案：** 将 `handle_feishu_error()` 调用包裹在 `try/except` 中，日志记录后继续正常返回 `CLIResult(success=False)`。

**修改文件：** [lark_base.py](src/tools/lark_base.py#L240-L284)

**修复效果：**
- CLI错误不再导致程序崩溃
- 工具层的 `if not result.success` 防御逻辑正常生效
- 错误信息通过 `CLIResult.error` 传递给上层，由Agent生成友好的错误回复

---

### 1.2 修复流式输出token丢失

**问题描述：** `astream()` 中用 `content != last_content` 来去重，当LLM连续输出相同token（如"的的"）时，第二个"的"会被错误过滤掉，导致流式输出内容缺失。

**技术方案：** 移除 `last_content` 比较逻辑，改为只过滤空chunk。同时将工具调用信息从文本流中分离，使用 `\x00TOOL_START:name` / `\x00TOOL_END` 标记工具事件，由 `main.py` 独立处理显示。

**修改文件：** [brain.py](src/agent/brain.py#L213-L232)、[main.py](main.py#L125-L142)

**修复效果：**
- 流式输出不再丢失任何token
- 工具调用信息不再混入 `full_response`，避免 `Live` 组件重复渲染
- 工具调用独立打印一次，界面干净整洁

---

### 1.3 修复DocumentLoader不支持Mock模式

**问题描述：** `DocumentLoader` 硬编码了 `LarkCLI()`，在Mock模式下调用飞书文档加载会直接失败。

**技术方案：** 统一使用 `get_cli()` 工厂函数，根据 `settings.mock_mode` 自动选择真实或模拟CLI。

**修改文件：** [document_loader.py](src/rag/document_loader.py#L15-L23)

**修复效果：** DocumentLoader 在Mock模式下正常工作，与其他工具模块行为一致。

---

## 二、架构解耦与代码质量（方向二）

### 2.1 统一CLI单例管理

**问题描述：** `note_tools.py` 和 `res_tools.py` 各自维护了一份完全重复的 `_cli` 全局变量和 `get_cli()` 函数，共约30行重复代码。且两个模块各自创建独立的CLI实例，可能造成资源浪费。

**技术方案：** 将 `get_cli()` 工厂函数提取到 `lark_base.py` 中统一管理，所有工具模块从同一处获取CLI单例实例。

**修改文件：**
- [lark_base.py](src/tools/lark_base.py#L640-L652) — 新增 `get_cli()` 函数
- [note_tools.py](src/tools/note_tools.py#L11) — 改为 `from .lark_base import get_cli`
- [res_tools.py](src/tools/res_tools.py#L11) — 改为 `from .lark_base import get_cli`
- [document_loader.py](src/rag/document_loader.py#L15) — 改为 `from ..tools.lark_base import get_cli`

**修复效果：**
- 消除3处重复的 `get_cli()` 实现
- 全局只有一个CLI实例，资源利用更合理
- 新增工具模块只需一行 `from .lark_base import get_cli` 即可使用

---

### 2.2 构建真正的RAG检索链

**问题描述：** RAG与Agent是"假集成"——`add_documents_to_store` 和 `search_documents_in_store` 只注册了工具，但文档加载→分块→向量化→检索的完整链路没有串联。`get_rag_prompt()` 和 `get_summary_prompt()` 被定义但从未调用。

**技术方案：** 新增两个端到端工具：
- `index_feishu_document`：串联 load → split → embed → store 的完整索引流程
- `rag_query`：从向量数据库检索最相关文档片段，返回结构化上下文

同时新增 `add_texts_with_dedup()` 方法，基于 `document_id` 实现先删后插的去重逻辑。

**修改文件：** [vector_store.py](src/rag/vector_store.py#L65-L100) — 新增 `IndexFeishuDocumentInput`、`RagQueryInput` 输入模型；新增 `add_texts_with_dedup`、`index_feishu_document`、`rag_query` 方法和工具

**修复效果：**
- Agent工具总数从14个增至18个
- RAG链路完整：飞书文档 → RecursiveCharacterTextSplitter分块 → 向量嵌入 → ChromaDB存储 → 相似度检索 → 结构化输出
- 向量库支持去重，重复索引同一文档不会产生冗余数据

---

### 2.3 补全多LLM提供商路由

**问题描述：** `settings.py` 配置了 `anthropic_api_key`、`zhipuai_api_key` 等多个提供商，但 `_create_llm()` 硬编码只创建 `ChatOpenAI` 实例，配置文件中的多模型选项形同虚设。

**技术方案：** 新增 `LLM_PROVIDER` 配置项（支持 `openai`/`anthropic`/`zhipuai`），`_create_llm()` 根据配置动态路由到不同的LLM客户端。Anthropic使用 `langchain_anthropic.ChatAnthropic`，智谱AI使用 OpenAI 兼容接口。

**修改文件：**
- [settings.py](src/config/settings.py#L20-L28) — 新增 `llm_provider`、`anthropic_model_name`、`zhipuai_model_name` 配置项
- [brain.py](src/agent/brain.py#L36-L72) — 重写 `_create_llm()` 为多提供商路由

**修复效果：**
- 切换LLM提供商只需修改 `.env` 中的 `LLM_PROVIDER` 即可
- 智谱AI使用 `https://open.bigmodel.cn/api/paas/v4` 兼容接口，无需额外依赖
- Anthropic 使用专用SDK `langchain_anthropic`，按需懒加载

---

### 2.4 修复FAISS初始化脏数据

**问题描述：** FAISS索引为空时会写入一条"初始化文档"占位，该数据永远不会被删除，会干扰所有后续的相似度检索结果。

**技术方案：** FAISS索引不存在时返回 `None`，首次写入时才创建索引。`similarity_search` 增加空索引保护。

**修改文件：** [vector_store.py](src/rag/vector_store.py#L108-L155)

**修复效果：**
- 向量库中不再有"初始化文档"脏数据
- 首次写入时自动创建FAISS索引
- 空索引查询时返回空列表而非报错

---

## 三、会话与记忆管理升级（方向三）

### 3.1 引入Token预算控制

**问题描述：** 会话历史无限累积，随对话轮次线性增长。长对话会撑爆LLM的context window，导致API报错或响应质量下降。

**技术方案：** 新增 `_estimate_tokens()` 和 `_trim_messages()` 方法。使用基于规则的token估算（中文约1.5 token/字，英文约0.4 token/字符），从最近的消息向前累积，超出 `MAX_HISTORY_TOKENS` 预算时裁剪最早的消息。

**修改文件：**
- [settings.py](src/config/settings.py#L42-L43) — 新增 `max_history_tokens` 配置项（默认4000）
- [brain.py](src/agent/brain.py#L112-L141) — 新增 `_estimate_tokens`、`_trim_messages` 方法
- [brain.py](src/agent/brain.py#L157-L253) — 三个执行方法均在发消息前调用 `_trim_messages`

**修复效果：**
- 长对话不会撑爆context window
- 历史消息裁剪时记录日志，方便调试
- 裁剪阈值可通过 `.env` 中的 `MAX_HISTORY_TOKENS` 配置

---

### 3.2 会话历史持久化（SQLite）

**问题描述：** 使用 `InMemoryChatMessageHistory`，程序重启后所有对话历史丢失。用户无法在不同运行之间保留上下文。

**技术方案：** 新增 `src/storage/chat_history.py` 模块，基于 SQLite 实现：
- `add_message()` — 写入单条消息
- `get_messages()` — 加载会话的所有消息（返回LangChain消息对象）
- `get_session_list()` — 获取所有会话列表
- `delete_session()` — 删除指定会话

使用线程本地存储（`threading.local`）确保多线程安全，WAL模式提升并发性能。`brain.py` 在首次访问会话时从SQLite加载历史，每次对话后自动持久化。

**修改文件：**
- 新建 [src/storage/chat_history.py](src/storage/chat_history.py) — SQLite会话存储
- 新建 [src/storage/__init__.py](src/storage/__init__.py) — 模块导出
- [brain.py](src/agent/brain.py#L20) — 导入 `get_chat_history_manager`
- [brain.py](src/agent/brain.py#L106-L127) — `_get_chat_history` 从SQLite加载，新增 `_save_to_store`

**修复效果：**
- 对话历史自动保存到 `data/chat_history.db`
- 程序重启后自动加载历史对话
- 支持多会话管理和会话列表查询

---

### 3.3 删除操作加入确认机制

**问题描述：** `delete_document` 工具没有任何二次确认机制。Agent可能在误解用户意图时直接删除文档，且操作不可撤销。

**技术方案：** `delete_document` 新增 `confirm` 参数（默认 `False`）。Agent首次调用时（`confirm=False`），工具返回确认提示；Agent向用户确认意图后，再次调用（`confirm=True`）才真正执行删除。

**修改文件：**
- [note_tools.py](src/tools/note_tools.py#L162-L187) — 修改 `DeleteDocumentInput` 和 `delete_document`
- [tests/test_document_crud.py](tests/test_document_crud.py#L158-L282) — 更新测试用例适配确认机制

**修复效果：**
- 删除操作必须经过用户确认，防止误删
- Agent会先向用户展示要删除的文档ID，等待确认后再执行
- 测试用例验证：未确认时返回提示，确认后正常删除

---

## 四、测试验证

### 4.1 文档CRUD测试

运行命令：
```bash
python tests/test_document_crud.py
```

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 创建文档 | ✅ 通过 | 空文档、带内容文档、空标题文档 |
| 获取文档 | ✅ 通过 | 不同ID均可获取 |
| 更新文档 | ✅ 通过 | 更新内容、空内容、大量内容 |
| 追加内容 | ✅ 通过 | 追加内容、空内容 |
| 删除文档 | ✅ 通过 | 未确认→提示，确认→删除 |
| 搜索文档 | ✅ 通过 | 不同关键词、指定数量 |
| 完整CRUD工作流 | ✅ 通过 | 创建→获取→更新→追加→搜索→删除全流程 |

### 4.2 流式输出测试

运行命令：
```bash
python tests/test_stream_tool_output.py
```

| 测试场景 | 工具调用次数 | 文本chunk数 | 状态 |
|---------|------------|------------|------|
| 创建文档 | 1次 | 276 | ✅ 正常 |
| 搜索文档 | 1次 | 341 | ✅ 正常 |
| 删除文档 | 1次 | 93 | ✅ 正常 |

---

## 五、修改文件汇总

| 文件 | 修改类型 | 涉及优化项 |
|------|---------|-----------|
| `src/tools/lark_base.py` | 修改 | 1.1, 2.1 |
| `src/tools/note_tools.py` | 修改 | 2.1, 3.3 |
| `src/tools/res_tools.py` | 修改 | 2.1 |
| `src/agent/brain.py` | 修改 | 1.2, 2.3, 3.1, 3.2 |
| `src/config/settings.py` | 修改 | 2.3, 3.1 |
| `src/rag/vector_store.py` | 修改 | 2.2, 2.4 |
| `src/rag/document_loader.py` | 修改 | 1.3, 2.1 |
| `src/storage/chat_history.py` | 新建 | 3.2 |
| `src/storage/__init__.py` | 新建 | 3.2 |
| `main.py` | 修改 | 1.2 |
| `tests/test_document_crud.py` | 修改 | 3.3 |

---

## 六、新增配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| LLM提供商 | `LLM_PROVIDER` | `openai` | 支持 `openai`/`anthropic`/`zhipuai` |
| Anthropic模型 | `ANTHROPIC_MODEL_NAME` | `claude-3-sonnet-20240229` | Anthropic模型名称 |
| 智谱AI模型 | `ZHIPUAI_MODEL_NAME` | `glm-4` | 智谱AI模型名称 |
| 历史消息token预算 | `MAX_HISTORY_TOKENS` | `4000` | 超出时自动裁剪最早消息 |
| 模拟模式 | `MOCK_MODE` | `false` | 设为true时使用模拟数据 |

---

## 七、待后续优化

| 方向 | 优先级 | 说明 |
|------|--------|------|
| API调用限流与重试 | 🟡 中 | 接入 `tenacity` 库实现指数退避重试 |
| 可观测性提升 | 🟡 中 | 展示工具输入参数和执行结果 |
| 依赖管理规范化 | 🟡 中 | 补全requirements.txt、锁定版本 |
| 测试体系完善 | 🟢 低 | 补充res_tools、vector_store、document_loader测试 |
| lark-cli命令格式验证 | 🟡 中 | 对照官方文档验证每个命令格式 |
