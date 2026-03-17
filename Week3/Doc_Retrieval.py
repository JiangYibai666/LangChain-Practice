import argparse
import os
import shutil
import sys

from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import FakeEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
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
    raise FileNotFoundError(
        "CSV file not found. Checked these paths:\n - " + searched
    )


def exercise_retrieval(llm: ChatGoogleGenerativeAI, csv_path: str = "products.csv") -> None:
    section("Document Retrieval (products.csv vector retrieval)")
    resolved_csv_path = resolve_csv_path(csv_path)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    embedding_backend = "Gemini embeddings"
    
    persist_directory = "./chroma_db"

    if os.path.exists(persist_directory):
        print(f"Found existing ChromaDB at '{persist_directory}'. Loading...")
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    else:
        print(f"Creating new ChromaDB from {resolved_csv_path}...")
        loader = CSVLoader(file_path=resolved_csv_path)
        docs = loader.load()

        try:
            vectorstore = Chroma.from_documents(
                documents=docs, 
                embedding=embeddings, 
                persist_directory=persist_directory
            )
        except GoogleGenerativeAIError as error:
            if "RESOURCE_EXHAUSTED" not in str(error):
                raise
            print("Embedding quota exceeded; falling back to FakeEmbeddings for this run.")
            embeddings = FakeEmbeddings(size=768)
            embedding_backend = "FakeEmbeddings fallback"
            
            vectorstore = Chroma.from_documents(
                documents=docs, 
                embedding=embeddings, 
                persist_directory=persist_directory
            )

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

    print(f"CSV: {resolved_csv_path}")
    print(f"Embeddings: {embedding_backend}")
    print("Interactive mode started. Type 'q' to quit.", flush=True)

    while True:
        print("\n" + "-" * 50)
        sys.stdout.write("Enter your query: ")
        sys.stdout.flush()
        
        line = sys.stdin.readline()
        if not line:
            break
            
        query = line.strip()
        
        if query.lower() in ["q", "quit", "exit"]:
            print("Exiting...", flush=True)
            break
            
        if not query:
            continue
            
        print(f"\n[Status] Processing query: '{query}'", flush=True)
        try:
            # Explicit retrieval check to debug if vector store is hanging
            retrieved_docs = retriever.invoke(query)
            print(f"[Status] Retrieved {len(retrieved_docs)} documents from ChromaDB.", flush=True)
            
            print("[Status] Sending context to LLM and generating answer...", flush=True)
            result = rag_chain.invoke(query)
            print(f"\nAnswer: {result}\n", flush=True)
        except Exception as e:
            print(f"\n[Error] An error occurred processing the query: {e}", flush=True)
            import traceback
            traceback.print_exc()


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
