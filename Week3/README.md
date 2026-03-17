# Week3 - SKP Production-like RAG (ChromaDB)

This folder contains a Week3 upgrade of the SKP practice into a production-like flow:
- Persistent vector storage with **ChromaDB**
- Ingestion pipeline (`ingest`)
- Single-turn QA (`ask`)
- Interactive QA loop (`chat`)

Main script: `SKP_New.py`

## 1) Prerequisites

- Python 3.10+ recommended
- A valid `GEMINI_API_KEY`

## 2) Install Dependencies

From this folder (`Week3`):

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

## 3) Environment Variables

Create a `.env` (in this folder or project root) with at least:

```env
GEMINI_API_KEY=your_api_key_here
```

Optional overrides:

```env
LLM_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/gemini-embedding-001
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION=skp_docs
RETRIEVAL_TOP_K=6
```

## 4) Quick Start (Recommended Order)

### Step A: Ingest documents into ChromaDB

```bash
python3 SKP_New.py --task ingest --csv products.csv
```

This will:
- Load `products.csv`
- Split documents into chunks
- Generate embeddings
- Persist vectors to ChromaDB (`./data/chroma` by default)

### Step B: Ask one question

```bash
python3 SKP_New.py --task ask --question "Find electronics between $10 and $20 with decent stock"
```

### Step C: Start interactive chat

```bash
python3 SKP_New.py --task chat
```

Type `exit` / `quit` / `q` to leave chat.

## 5) Useful Commands

Run all legacy + retrieval tasks:

```bash
python3 SKP_New.py --task all
```

Run only retrieval task:

```bash
python3 SKP_New.py --task retrieval
```

Use custom Chroma storage/collection:

```bash
python3 SKP_New.py --task ingest \
  --persist-dir ./data/chroma_demo \
  --collection skp_demo
```

Tune retrieval and chunk settings:

```bash
python3 SKP_New.py --task ingest --chunk-size 500 --chunk-overlap 50
python3 SKP_New.py --task ask --question "What is the stock of Smart Plug?" --k 6
```

## 6) Script Tasks Overview

`--task` supports:
- `basic`
- `json`
- `sequential`
- `router`
- `retrieval`
- `ingest`
- `ask`
- `chat`
- `all`

## 7) Expected Outputs

For `ask` / `chat`, output includes:
- `answer`
- `sources` (source file, row, chunk index)
- `latency_s`

This allows basic traceability in a production-like setup.

## 8) Troubleshooting

1. `GEMINI_API_KEY` missing
- Ensure `.env` is present and key is valid.

2. `ModuleNotFoundError` for LangChain/Chroma packages
- Re-run dependency installation in the same Python interpreter used to run script.

3. Empty or weak retrieval results
- Run `ingest` first.
- Increase `--k`.
- Check `--collection` and `--persist-dir` are consistent between ingest and ask/chat.

4. API quota/rate issues
- Retry later, reduce request frequency, or switch to a smaller test flow.

## 9) Notes

- `Doc_Retrieval.py` is an additional retrieval practice script.
- For the production-like path, prefer `SKP_New.py`.
