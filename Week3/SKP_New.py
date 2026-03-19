import argparse
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from dotenv import find_dotenv, load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_text_splitters import RecursiveCharacterTextSplitter


def bootstrap_env() -> None:
    """Load local environment variables and validate mandatory API key."""
    load_dotenv(find_dotenv())
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("未读取到 GEMINI_API_KEY，请先在 .env 中配置")


def get_llm(model: str | None = None, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Create a Gemini chat model with configurable model name/temperature."""
    llm_model = model or os.getenv("LLM_MODEL", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(model=llm_model, temperature=temperature)


def get_embeddings(model: str | None = None) -> GoogleGenerativeAIEmbeddings:
    """Create embedding model used for vector indexing and retrieval."""
    embedding_model = model or os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    return GoogleGenerativeAIEmbeddings(model=embedding_model)


def get_embeddings_with_fallback(model: str | None = None) -> Any:
    """Try real Gemini embeddings, fall back to fake embeddings on quota exhaustion."""
    embedding_model = model or os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    try:
        return GoogleGenerativeAIEmbeddings(model=embedding_model)
    except GoogleGenerativeAIError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            print("[WARN] Gemini embedding quota耗尽，将回退 FakeEmbeddings。")
            return FakeEmbeddings(size=768)
        raise


def section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


# -----------------------------------------------------------------------------
# Legacy SKP practice tasks (kept for continuity with Week2 exercises)
# -----------------------------------------------------------------------------
def exercise_basic_prompt(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-1] PromptTemplate + 基础链")
    prompt = ChatPromptTemplate.from_template(
        "You are a concise assistant. Summarize the product in 1 sentence. Product: {product}"
    )
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"product": "Smart Plug: remotely turn devices on/off via app"})
    print(result)


def exercise_structured_output(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-2] 结构化输出（JSON Parser）")
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_template(
        """Return valid JSON only with keys: category, risk_level, reason.
Text: {text}"""
    )
    chain = prompt | llm | parser
    result = chain.invoke(
        {
            "text": "Monitor (24 inch) 149.00 stock 30. This is high-value inventory with limited stock."
        }
    )
    print(result)


def exercise_sequential(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-3] 顺序链（Sequential via LCEL）")
    translate_prompt = ChatPromptTemplate.from_template("Translate to Chinese: {text}")
    summarize_prompt = ChatPromptTemplate.from_template(
        "用不超过12个中文字符总结这句话：{text}"
    )

    translate_chain = translate_prompt | llm | StrOutputParser()
    summarize_chain = summarize_prompt | llm | StrOutputParser()

    source_text = "Smart Bulb can be voice-controlled and scheduled automatically."
    zh_text = translate_chain.invoke({"text": source_text})
    short_summary = summarize_chain.invoke({"text": zh_text})

    print("原文:", source_text)
    print("翻译:", zh_text)
    print("总结:", short_summary)


def exercise_router(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-4] 路由链（RunnableBranch）")
    physics_prompt = ChatPromptTemplate.from_template(
        "You are a physics tutor. Answer briefly with formulas when needed. Q: {question}"
    )
    math_prompt = ChatPromptTemplate.from_template(
        "You are a math tutor. Show concise step-by-step solution. Q: {question}"
    )
    history_prompt = ChatPromptTemplate.from_template(
        "You are a history tutor. Give context then answer. Q: {question}"
    )
    cs_prompt = ChatPromptTemplate.from_template(
        "You are a computer science tutor. Include practical explanation. Q: {question}"
    )
    default_prompt = ChatPromptTemplate.from_template(
        "You are a helpful tutor. Answer clearly. Q: {question}"
    )

    physics_chain = physics_prompt | llm | StrOutputParser()
    math_chain = math_prompt | llm | StrOutputParser()
    history_chain = history_prompt | llm | StrOutputParser()
    cs_chain = cs_prompt | llm | StrOutputParser()
    default_chain = default_prompt | llm | StrOutputParser()

    def route(x: dict) -> Literal["physics", "math", "history", "cs", "default"]:
        q = x["question"].lower()
        if any(k in q for k in ["radiation", "force", "energy", "velocity", "newton"]):
            return "physics"
        if any(k in q for k in ["equation", "integral", "derivative", "probability", "solve"]):
            return "math"
        if any(k in q for k in ["war", "empire", "dynasty", "revolution", "history"]):
            return "history"
        if any(k in q for k in ["algorithm", "python", "database", "complexity", "computer"]):
            return "cs"
        return "default"

    branched_chain = RunnableBranch(
        (lambda x: route(x) == "physics", physics_chain),
        (lambda x: route(x) == "math", math_chain),
        (lambda x: route(x) == "history", history_chain),
        (lambda x: route(x) == "cs", cs_chain),
        default_chain,
    )

    question = "What is black body radiation?"
    result = branched_chain.invoke({"question": question})
    print("路由结果问题:", question)
    print(result)


# -----------------------------------------------------------------------------
# Week3 production-like extension: ChromaDB persistent indexing + Q&A
# -----------------------------------------------------------------------------
def build_chroma_store(
    persist_dir: str,
    collection_name: str,
    embeddings: GoogleGenerativeAIEmbeddings,
) -> Chroma:
    """Create or load a persistent Chroma collection."""
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def format_docs(docs: List[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def resolve_csv_path(csv_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        csv_path,
        os.path.join(script_dir, csv_path),
        os.path.join(script_dir, "..", csv_path),
        os.path.join(script_dir, "..", "Week3", csv_path),
    ]

    seen = set()
    normalized_candidates = []
    for path in candidates:
        absolute_path = os.path.abspath(path)
        if absolute_path not in seen:
            seen.add(absolute_path)
            normalized_candidates.append(absolute_path)

    for path in normalized_candidates:
        if os.path.exists(path):
            return path

    searched = "\n - ".join(normalized_candidates)
    raise FileNotFoundError("CSV 文件未找到，检查以下路径：\n - " + searched)


def stable_id(doc: Document, chunk_index: int) -> str:
    """Generate deterministic IDs to support safe re-ingestion (upsert behavior)."""
    source = doc.metadata.get("source", "unknown_source")
    row = doc.metadata.get("row", "unknown_row")
    raw = f"{source}|{row}|{chunk_index}|{doc.page_content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def ingest_documents(
    csv_path: str,
    persist_dir: str,
    collection_name: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    section("[Week3] INGEST -> ChromaDB")

    csv_path = resolve_csv_path(csv_path)
    loader = CSVLoader(file_path=csv_path)
    docs = loader.load()
    if not docs:
        raise ValueError(f"没有从 {csv_path} 读取到文档")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    split_docs = splitter.split_documents(docs)

    # Enrich metadata for tracing and future governance.
    now_iso = datetime.now(timezone.utc).isoformat()
    for i, doc in enumerate(split_docs):
        doc.metadata["ingested_at"] = now_iso
        doc.metadata["chunk_index"] = i

    ids = [stable_id(d, i) for i, d in enumerate(split_docs)]

    embeddings = get_embeddings_with_fallback(embedding_model)
    vectorstore = build_chroma_store(persist_dir, collection_name, embeddings)

    start = time.perf_counter()
    try:
        vectorstore.add_documents(split_docs, ids=ids)
    except GoogleGenerativeAIError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            print("[WARN] GPU额度耗尽。使用 FakeEmbeddings 重新索引（仅本次）。")
            embeddings = FakeEmbeddings(size=768)
            vectorstore = build_chroma_store(persist_dir, collection_name, embeddings)
            vectorstore.add_documents(split_docs, ids=ids)
        else:
            raise
    duration = time.perf_counter() - start

    print(f"csv_path           : {csv_path}")
    print(f"persist_dir        : {persist_dir}")
    print(f"collection_name    : {collection_name}")
    print(f"raw_docs           : {len(docs)}")
    print(f"chunks_indexed     : {len(split_docs)}")
    print(f"ingest_duration_s  : {duration:.3f}")


def get_retriever(
    persist_dir: str,
    collection_name: str,
    embedding_model: str,
    k: int,
):
    try:
        embeddings = get_embeddings_with_fallback(embedding_model)
        vectorstore = build_chroma_store(persist_dir, collection_name, embeddings)
    except GoogleGenerativeAIError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            print("[WARN] Gemini embedding quota耗尽。改用 FakeEmbeddings 进行检索。")
            embeddings = FakeEmbeddings(size=768)
            vectorstore = build_chroma_store(persist_dir, collection_name, embeddings)
        else:
            raise

    return vectorstore.as_retriever(search_kwargs={"k": k})


def ask_once(
    question: str,
    persist_dir: str,
    collection_name: str,
    embedding_model: str,
    llm_model: str,
    k: int,
) -> Dict[str, Any]:
    """Run one retrieval-augmented question and return answer with source docs."""
    retriever = get_retriever(persist_dir, collection_name, embedding_model, k)
    llm = get_llm(model=llm_model, temperature=0)

    rag_prompt = ChatPromptTemplate.from_template(
        """You are a product assistant.
Use ONLY the retrieved context below to answer the question.
If the context is insufficient, say exactly: I don't know based on the provided data.

Context:
{context}

Question: {question}
"""
    )

    # Attach retrieved docs directly so we can print sources in final output.
    chain = (
        RunnablePassthrough.assign(retrieved_docs=lambda x: retriever.invoke(x["question"]))
        | RunnablePassthrough.assign(context=lambda x: format_docs(x["retrieved_docs"]))
        | RunnablePassthrough.assign(
            answer=(rag_prompt | llm | StrOutputParser())
        )
    )

    start = time.perf_counter()
    out = chain.invoke({"question": question})
    duration = time.perf_counter() - start

    print(f"[Status] Retrieved {len(out.get('retrieved_docs', []))} documents from ChromaDB.")

    source_rows: List[Dict[str, Any]] = []
    for doc in out["retrieved_docs"]:
        source_rows.append(
            {
                "source": doc.metadata.get("source", "unknown"),
                "row": doc.metadata.get("row", "unknown"),
                "chunk_index": doc.metadata.get("chunk_index", "unknown"),
            }
        )

    return {
        "answer": out["answer"],
        "sources": source_rows,
        "latency_s": round(duration, 3),
    }


def chat_loop(
    persist_dir: str,
    collection_name: str,
    embedding_model: str,
    llm_model: str,
    k: int,
) -> None:
    section("[Week3] INTERACTIVE CHAT (type 'exit' to quit)")

    while True:
        question = input("\nYou> ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            print("Bye.")
            break
        if not question:
            continue

        result = ask_once(
            question=question,
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_model=embedding_model,
            llm_model=llm_model,
            k=k,
        )

        print("\nAssistant>")
        print(result["answer"])
        print(f"\n[latency_s] {result['latency_s']}")
        print("[sources]")
        for idx, src in enumerate(result["sources"], start=1):
            print(
                f"  {idx}. source={src['source']} row={src['row']} chunk_index={src['chunk_index']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Week3 SKP: production-like ChromaDB RAG")
    parser.add_argument(
        "--task",
        choices=[
            "basic",
            "json",
            "sequential",
            "router",
            "retrieval",
            "ingest",
            "ask",
            "chat",
            "all",
        ],
        default="all",
    )

    parser.add_argument("--csv", default="products.csv", help="CSV path for ingest/retrieval")
    parser.add_argument("--question", default="", help="Question for --task ask")

    parser.add_argument(
        "--persist-dir",
        default=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
        help="Persistent folder for ChromaDB",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "skp_docs"),
        help="Chroma collection name",
    )

    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001"),
    )

    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--k", type=int, default=int(os.getenv("RETRIEVAL_TOP_K", "6")))
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=50)

    args = parser.parse_args()

    bootstrap_env()
    llm = get_llm(model=args.llm_model, temperature=args.temperature)

    if args.task in ["basic", "all"]:
        exercise_basic_prompt(llm)
    if args.task in ["json", "all"]:
        exercise_structured_output(llm)
    if args.task in ["sequential", "all"]:
        exercise_sequential(llm)
    if args.task in ["router", "all"]:
        exercise_router(llm)

    # Keep retrieval task for backwards compatibility but now use persistent Chroma retriever.
    if args.task in ["retrieval", "all"]:
        section("[SKP-5 / Week3] 文档检索（ChromaDB persistent）")
        result = ask_once(
            question="Find electronics between $10 and $20 with decent stock, and explain why.",
            persist_dir=args.persist_dir,
            collection_name=args.collection,
            embedding_model=args.embedding_model,
            llm_model=args.llm_model,
            k=args.k,
        )
        print("answer:")
        print(result["answer"])
        print("sources:")
        for src in result["sources"]:
            print(src)

    if args.task == "ingest":
        ingest_documents(
            csv_path=args.csv,
            persist_dir=args.persist_dir,
            collection_name=args.collection,
            embedding_model=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )

    if args.task == "ask":
        if not args.question:
            raise ValueError("--task ask 需要提供 --question")
        result = ask_once(
            question=args.question,
            persist_dir=args.persist_dir,
            collection_name=args.collection,
            embedding_model=args.embedding_model,
            llm_model=args.llm_model,
            k=args.k,
        )
        print("answer:")
        print(result["answer"])
        print("sources:")
        for src in result["sources"]:
            print(src)

    if args.task == "chat":
        chat_loop(
            persist_dir=args.persist_dir,
            collection_name=args.collection,
            embedding_model=args.embedding_model,
            llm_model=args.llm_model,
            k=args.k,
        )


if __name__ == "__main__":
    main()
