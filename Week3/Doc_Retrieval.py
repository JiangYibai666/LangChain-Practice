import argparse
import os

from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
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
    section("Document Retrieval (products.csv vector retrieval)")
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
    parser = argparse.ArgumentParser(description="SKP Retrieval Practice")
    parser.add_argument(
        "--csv",
        default="products.csv",
        help="CSV path for retrieval task (default: products.csv)",
    )
    args = parser.parse_args()

    bootstrap_env()
    llm = get_llm()

    exercise_retrieval(llm, csv_path=args.csv)


if __name__ == "__main__":
    main()
