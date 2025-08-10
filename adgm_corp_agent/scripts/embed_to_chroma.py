# scripts/embed_to_chroma.py
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma

def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def split_text_into_chunks(text: str, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)

def create_chroma_from_texts(texts, persist_dir="adgm_chromadb", metadatas=None):
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma.from_texts(texts, embedding=emb, persist_directory=persist_dir, metadatas=metadatas)
    db.persist()
    print("ChromaDB persisted to:", persist_dir)
    return db

if __name__ == "__main__":
    txt_path = "data/adgm_data_sources.txt"
    if not Path(txt_path).exists():
        raise SystemExit("Run scripts/extract_pdf.py first to create data/adgm_data_sources.txt")
    text = load_text(txt_path)
    chunks = split_text_into_chunks(text)
    # simple metadata - can be extended per source
    metadatas = [{"source":"Data Sources.pdf"} for _ in chunks]
    create_chroma_from_texts(chunks, persist_dir="adgm_chromadb", metadatas=metadatas)
