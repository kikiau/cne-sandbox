import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

load_dotenv()

def ingest_articles():
    articles_path = Path("data/articles")

    loader = DirectoryLoader(
        str(articles_path),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True
    )
    documents = loader.load()

    print(f"Loaded {len(documents)} articles")

    for doc in documents:
        print(f"- {doc.metadata.get('source', 'unknown')}: {len(doc.page_content)} characters")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(documents)

    print(f"Split into {len(chunks)} chunks")

    if len(chunks) == 0:
        print("No chunks created. Stopping.")
        return

    embeddings = OpenAIEmbeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="data/chroma_db"
    )

    print("Ingestion complete. Vector database saved to data/chroma_db")
    return vectorstore

if __name__ == "__main__":
    ingest_articles()