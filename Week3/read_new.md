# Week3 - 类生产级 SKP RAG（ChromaDB）

此文件夹包含将 SKP 练习升级为类生产流程的 Week3 版本：
- 使用 **ChromaDB** 的持久向量存储
- 数据摄取管道（`ingest`）
- 单轮问答（`ask`）
- 交互式 QA 循环（`chat`）

主脚本：`SKP_New.py`

## 1) 先决条件

- 建议 Python 3.10+
- 有效的 `GEMINI_API_KEY`

## 2) 安装依赖

在此文件夹（`Week3`）下运行：

```bash
python3 -m pip install -U pip
python3 -m pip install \
  python-dotenv \
  langchain-core \
  langchain-community \
  langchain-google-genai \
  langchain-text-splitters \
  langchain-chroma \
  chromadb
```

## 3) 环境变量

在此文件夹或项目根目录中创建 `.env`，至少包括：

```env
GEMINI_API_KEY=your_api_key_here
```

可选的覆盖项：

```env
LLM_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION=skp_docs
RETRIEVAL_TOP_K=6
```

附加 SKP_New 稳健性

- `CSV` 路径会自动解析：当前目录、上一级目录、`Week3` 子目录。
- 发生 `RESOURCE_EXHAUSTED` 时自动回退 `FakeEmbeddings`。
- `ask/chat` 时会输出检索文档数量：`[Status] Retrieved X documents from ChromaDB.`。

## 4) 快速开始（推荐顺序）

### 步骤 A：将文档摄取到 ChromaDB

```bash
python3 SKP_New.py --task ingest --csv products.csv
```

此操作将：
- 加载 `products.csv`
- 将文档拆分为文本块
- 生成嵌入
- 将向量保存到 ChromaDB（默认 `./data/chroma`）

### 步骤 B：问一个问题

```bash
python3 SKP_New.py --task ask --question "Find electronics between $10 and $20 with decent stock"
```

### 步骤 C：启动交互式聊天

```bash
python3 SKP_New.py --task chat
```

输入 `exit` / `quit` / `q` 退出聊天。

## 5) 常用命令

运行所有旧版+检索任务：

```bash
python3 SKP_New.py --task all
```

仅运行检索任务：

```bash
python3 SKP_New.py --task retrieval
```

使用自定义 Chroma 存储/集合：

```bash
python3 SKP_New.py --task ingest \
  --persist-dir ./data/chroma_demo \
  --collection skp_demo
```

调整检索和分块设置：

```bash
python3 SKP_New.py --task ingest --chunk-size 500 --chunk-overlap 50
python3 SKP_New.py --task ask --question "What is the stock of Smart Plug?" --k 6
```

## 6) 脚本任务概览

`--task` 支持：
- `basic`
- `json`
- `sequential`
- `router`
- `retrieval`
- `ingest`
- `ask`
- `chat`
- `all`

## 7) 期望输出

对于 `ask` / `chat`，输出包括：
- `answer`
- `sources`（源文件、行号、块索引）
- `latency_s`

这提供了类生产环境下的基本可追溯性。

## 8) 故障排查

1. 缺少 `GEMINI_API_KEY`
- 确保 `.env` 存在且密钥有效。

2. 找不到 LangChain/Chroma 模块（`ModuleNotFoundError`）
- 在与运行脚本相同的 Python 解释器中重新安装依赖。

3. 检索结果为空或较弱
- 先运行 `ingest`。
- 提高 `--k`。
- 检查 `--collection` 和 `--persist-dir` 在 ingest、ask、chat 之间一致。

4. API 配额/速率问题
- 稍后重试，降低请求频率，或切换到更小的测试流程。

## 9) 备注

- `Doc_Retrieval.py` 是一个额外的检索练习脚本。
- 对于类生产路径，优先使用 `SKP_New.py`。
