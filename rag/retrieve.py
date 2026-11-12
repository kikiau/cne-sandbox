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
You are a Community Policy assistant. Analyze the user's issue against the provided policy articles and give clear directional guidance.

Follow this exact structure in your response:

**Policy that applies:** [Name the most relevant policy or say "Not clearly covered"]

**Key points from articles:**
- [Bullet the most relevant rules or statements from the context]

**Recommended action:**
[One of: Self-resolve with guidance / Cancel + escalate / Warn or remove content / Escalate to Community Policy / Gather more information]

**Next steps or questions to ask:**
- [What the submitter or agent should do next, or what additional info is needed]

**Gaps:**
[Note anything the articles do not cover, or write "None"]

Use ONLY the provided context. Do not invent policies.

Context:
{context}

User issue:
{question}

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

