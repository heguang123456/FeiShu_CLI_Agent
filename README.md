﻿﻿﻿﻿﻿# 飞书CLI笔记智能体 (NoteAgent)

基于 LangChain 和飞书CLI 的智能笔记管理助手。

## 功能特性

- **智能笔记管理**：通过自然语言创建、更新、搜索飞书文档
- **资源自动整理**：搜索群聊消息、多维表格、知识库文章
- **知识检索增强**：基于RAG技术的文档语义搜索
- **智能体自主规划**：多步骤任务拆解和自动执行

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填入您的配置：

```bash
cp .env.example .env
```

主要配置项：
- `OPENAI_API_KEY`：OpenAI API密钥
- `OPENAI_API_BASE`：API基础URL（可选）
- `OPENAI_MODEL_NAME`：使用的模型名称

### 3. 启动程序

**Windows用户**：
```bash
start.bat
```

**其他系统**：
```bash
python main.py
```

## 使用指南

### 基本命令

- 直接输入问题或指令，与AI助手对话
- `/help` - 显示帮助信息
- `/tools` - 显示可用工具列表
- `/history` - 显示对话历史
- `/clear` - 清除对话历史
- `/quit` 或 `/exit` - 退出程序

### 示例对话

```
👤 您: 帮我创建一个会议纪要文档
🤖 助手: 我来帮您创建会议纪要文档...

👤 您: 搜索关于项目进度的群聊消息
🤖 助手: 正在搜索相关消息...

👤 您: 把这段内容整理成周报
🤖 助手: 我来帮您整理成周报格式...
```

## 项目结构

```
笔记智能体/
├── .env                  # 环境变量配置
├── requirements.txt      # 依赖包列表
├── start.bat             # Windows一键启动脚本
├── main.py               # 命令行交互入口
└── src/
    ├── __init__.py
    ├── agent/            # Agent核心大脑
    │   ├── brain.py
    │   └── prompts.py
    ├── rag/              # 知识检索与RAG
    │   ├── vector_store.py
    │   └── document_loader.py
    ├── tools/            # 飞书CLI工具箱
    │   ├── lark_base.py
    │   ├── note_tools.py
    │   └── res_tools.py
    └── config/           # 配置与基础设施
        └── settings.py
```

## 配置说明

### LLM配置

支持多种LLM提供商：
- OpenAI (默认)
- 其他兼容OpenAI API的服务

### 飞书CLI配置

确保已安装飞书CLI并登录：
```bash
# 安装飞书CLI
# 参考: https://github.com/larksuite/cli

# 登录飞书
lark-cli auth login
```

## 开发说明

### 核心原则

- 大模型与智能体逻辑工作量占比 > 50%
- 连接层和工具链尽量简化
- 核心复杂度聚焦在LangChain的RAG、Tool Calling和Agent状态机

### 技术栈

- **LangChain**：Agent框架
- **OpenAI**：大语言模型
- **Chroma/FAISS**：向量数据库
- **Rich**：命令行界面美化
- **Pydantic**：配置管理

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确

2. **飞书CLI未登录**
   - 执行 `lark-cli auth login` 重新登录

3. **依赖包安装失败**
   - 尝试使用 `pip install --user -r requirements.txt`

4. **编码错误**
   - 确保系统支持UTF-8编码

## 许可证

MIT License