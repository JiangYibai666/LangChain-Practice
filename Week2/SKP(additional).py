import argparse
import os
from typing import Literal

from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def bootstrap_env() -> None:
    load_dotenv(find_dotenv())
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not found. Please configure it in .env first.")


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=temperature,
        max_retries=3
    )


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def exercise_basic_prompt(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-1] PromptTemplate + Basic Chain")
    prompt = ChatPromptTemplate.from_template(
        "You are a concise assistant. Summarize the product in 1 sentence. Product: {product}"
    )
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"product": "Smart Plug: remotely turn devices on/off via app"})
    print(result)


def exercise_structured_output(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-2] Structured Output (JSON Parser)")
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
    section("[SKP-3] Sequential Chain (via LCEL)")
    summarize_prompt = ChatPromptTemplate.from_template(
        "Summarize this sentence in no more than 20 English words: {text}"
    )

    summarize_chain = summarize_prompt | llm | StrOutputParser()

    source_text = "Smart Bulb can be voice-controlled and scheduled automatically."
    short_summary = summarize_chain.invoke({"text": source_text})

    print("Original:", source_text)
    print("Summary:", short_summary)


def exercise_router(llm: ChatGoogleGenerativeAI) -> None:
    section("[SKP-4] Router Chain (without deprecated MultiPromptChain)")
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
    print("Routed question:", question)
    print(result)


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def resolve_csv_path(csv_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        csv_path,
        os.path.join(script_dir, csv_path),
        os.path.join(script_dir, "..", csv_path),
        os.path.join(script_dir, "..", "Week1", csv_path),
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
    raise FileNotFoundError(
        "CSV file not found. Checked these paths:\n - " + searched
    )


def exercise_retrieval(llm: ChatGoogleGenerativeAI, csv_path: str = "products.csv") -> None:
    section("[SKP-5] Document Retrieval (products.csv vector retrieval)")
    resolved_csv_path = resolve_csv_path(csv_path)
    loader = CSVLoader(file_path=resolved_csv_path)
    docs = loader.load()

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    embedding_backend = "Gemini embeddings"
    try:
        vectorstore = InMemoryVectorStore.from_documents(docs, embeddings)
    except GoogleGenerativeAIError as error:
        if "RESOURCE_EXHAUSTED" not in str(error):
            raise
        print("Embedding quota exceeded; falling back to FakeEmbeddings for this run.")
        embeddings = FakeEmbeddings(size=768)
        embedding_backend = "FakeEmbeddings fallback"
        vectorstore = InMemoryVectorStore.from_documents(docs, embeddings)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    rag_prompt = ChatPromptTemplate.from_template(
        """You are a product assistant.
Use only the context to answer. If missing, say you don't know.

Context:
{context}

Question: {question}
"""
    )

    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    query = "Find electronics between $10 and $20 with decent stock, and explain why."
    result = rag_chain.invoke(query)
    print("CSV:", resolved_csv_path)
    print("Embeddings:", embedding_backend)
    print("Query:", query)
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="SKP additional LangChain practice")
    parser.add_argument(
        "--task",
        choices=["basic", "json", "sequential", "router", "retrieval", "all"],
        default="all",
        help="Select which SKP practice task to run",
    )
    parser.add_argument(
        "--csv",
        default="products.csv",
        help="CSV path for retrieval task (default: products.csv)",
    )
    args = parser.parse_args()

    bootstrap_env()
    llm = get_llm()

    if args.task in ["basic", "all"]:
        exercise_basic_prompt(llm)
    if args.task in ["json", "all"]:
        exercise_structured_output(llm)
    if args.task in ["sequential", "all"]:
        exercise_sequential(llm)
    if args.task in ["router", "all"]:
        exercise_router(llm)
    if args.task in ["retrieval", "all"]:
        exercise_retrieval(llm, csv_path=args.csv)


if __name__ == "__main__":
    main()
