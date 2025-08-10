# scripts/test_retrieval.py
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma

def get_retriever(persist_dir="adgm_chromadb", k=5):
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=persist_dir, embedding_function=emb)
    retriever = db.as_retriever(search_kwargs={"k": k})
    return retriever

if __name__ == "__main__":
    retriever = get_retriever()
    query = "What documents are required for company incorporation in ADGM?"
    docs = retriever.get_relevant_documents(query)
    print("Top chunks:\n")
    for i, d in enumerate(docs, 1):
        print(f"--- Chunk {i} ---")
        print(d.page_content[:800])
        print()
