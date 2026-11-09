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
You are a helpful Community Policy assistant. Use the following articles to answer the user's issue.

Articles:
{context}

User issue: {question}

Give a clear, concise answer. At the end, list the most relevant article titles.
If the articles do not contain enough information, say so.
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
    # Get the raw documents first so we can log them
    docs = retriever.invoke(question)
    answer = rag_chain.invoke(question)
    
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        # Extract just the filename
        filename = source.split("/")[-1].replace(".md", "").replace("-", " ").title()
        sources.append(filename)
    
    return answer, sources

if __name__ == "__main__":
    test_question = "My account was restricted, how do I appeal?"
    answer, sources = get_answer(test_question)
    print(answer)
    print("\nSources:", sources)

