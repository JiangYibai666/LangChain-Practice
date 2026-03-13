import argparse
import os
from typing import Literal

from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def bootstrap_env() -> None:
    load_dotenv(find_dotenv())
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("未读取到 GEMINI_API_KEY，请先在 .env 中配置")


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temperature)


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


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
    section("[SKP-4] 路由链（不使用已弃用 MultiPromptChain）")
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


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def exercise_retrieval(llm: ChatGoogleGenerativeAI, csv_path: str = "products.csv") -> None:
    section("[SKP-5] 文档检索（products.csv 向量检索）")
    loader = CSVLoader(file_path=csv_path)
    docs = loader.load()

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vectorstore = DocArrayInMemorySearch.from_documents(docs, embeddings)
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
    print("查询:", query)
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
