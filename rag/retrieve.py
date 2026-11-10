from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

embeddings = OpenAIEmbeddings()
vectorstore = Chroma(
    persist_directory="data/chroma_db",
    embedding_function=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_template("""
You are a helpful Community Policy assistant. Answer the user's issue using ONLY the information from the provided policy articles.

If the articles contain relevant information, give a clear, direct answer and mention the specific policy points.
If the articles do not contain enough information to answer fully, say so briefly and still share whatever relevant guidance is available.

Context from policy articles:
{context}

User issue: {question}

Answer:
""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def get_answer(question: str):
    docs = retriever.invoke(question)
    answer = rag_chain.invoke(question)
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        filename = source.split("/")[-1].replace(".md", "").replace("-", " ").title()
        if filename not in sources:
            sources.append(filename)
    return answer, sources


if __name__ == "__main__":
    test_question = "Guest reported a recording device that is not powered on. What policy is it under?"
    answer, sources = get_answer(test_question)
    print(answer)
    print("\nSources:", sources)

