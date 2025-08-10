import streamlit as st
from pathlib import Path
from app.docx_utils import extract_text_from_docx
from app.review_pipeline import get_retriever, classify_doc_by_text, review_single_docx, detect_overall_process
import ollama
from streamlit_chat import message 

st.set_page_config(page_title="ADGM Corporate Agent", layout="wide")

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to:", ["📃 Document Review", "💬 ADGM Chatbot"])

retriever = get_retriever()  # Initialize once

# -------------------------------
# PAGE 1: Document Review
# -------------------------------
if page == "📃 Document Review":
    st.title("🏦 ADGM Corporate Agent — Document Intelligence")
    st.info("⬆️ Upload `.docx` files for checklist verification and compliance review. Uses TinyLlama + ChromaDB for RAG.")

    uploaded_files = st.file_uploader("Upload .docx files", type=["docx"], accept_multiple_files=True)

    if st.button("▶️ Run Embedding/Index (if first time)"):
        st.warning("Run the embedding scripts in terminal: `scripts/extract_pdf.py` then `scripts/embed_to_chroma.py`")

    if uploaded_files:
        save_dir = Path("uploads")
        save_dir.mkdir(exist_ok=True)
        saved_paths = []
        for f in uploaded_files:
            p = save_dir / f.name
            p.write_bytes(f.getbuffer())
            saved_paths.append(str(p))
        st.success(f"⬇️ Saved {len(saved_paths)} files to uploads/")

        # Classification
        doc_types = []
        st.header("📄 Detected Document Types")
        for p in saved_paths:
            text = extract_text_from_docx(p)
            dtype = classify_doc_by_text(text)
            doc_types.append(dtype)
            st.write(f"- **{Path(p).name}**: {dtype}")

        # Detect process and checklist
        process_info = detect_overall_process(doc_types)
        st.header("🗂 Detected Process / Checklist Status")
        st.json(process_info)

        if len(process_info.get("missing_documents", [])) > 0:
            st.warning(f"Missing documents: {process_info['missing_documents']}")
        else:
            st.success("✅ All required documents appear present.")

        if st.button("Run Compliance Review (RAG + TinyLlama)"):
            results = []
            for p in saved_paths:
                parsed, out_path = review_single_docx(p, retriever)
                results.append({"input_file": p, "reviewed_file": out_path, "parsed": parsed})
            st.header("🔍 Review Results")
            for r in results:
                st.subheader(f"{Path(r['input_file']).name} — {r['parsed'].get('num_red_flags', 0)} Red Flags")
                st.json(r["parsed"])
                with open(r["reviewed_file"], "rb") as fh:
                    st.download_button("⬇️ Download reviewed docx", fh.read(), file_name=Path(r["reviewed_file"]).name)

# -------------------------------
# PAGE 2: Chatbot
# -------------------------------
elif page == "💬 ADGM Chatbot":
    st.title("💬 ADGM Chatbot")
    st.info("Ask questions about ADGM requirements. Uses RAG with TinyLlama + ChromaDB.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # (user_msg, bot_msg, sources)

    # Render past chat
    for i, (user_msg, bot_msg, source_blocks) in enumerate(st.session_state.chat_history):
        message(user_msg, is_user=True, key=f"user_{i}", avatar_style="pixel-art-neutral")
        message(bot_msg, key=f"bot_{i}", avatar_style="bottts")
        if source_blocks:
            with st.expander("📚 Click to view sources"):
                for s in source_blocks:
                    st.markdown(s)

    # Input
    with st.container():
        query = st.text_input("Your question:", key="input_query")
        if st.button("Get Answer", key="send_btn") and query.strip():
            docs = retriever.get_relevant_documents(query)

            context = "\n\n---\n\n".join([d.page_content for d in docs])

            prompt = f"""You are an ADGM expert assistant. Use the following ADGM reference information to answer the question concisely. Cite sources as needed.

ADGM Reference Info:
{context}

Question:
{query}

Answer with relevant citations:
"""
            resp = ollama.chat(model="tinyllama", messages=[{"role": "user", "content": prompt}])
            answer = resp.get("message", {}).get("content", "")

            # Prepare sources
            source_blocks = [
                f"**Source {i}:**\n{d.page_content[:1000]}"
                for i, d in enumerate(docs, 1)
            ]

            st.session_state.chat_history.append((query, answer, source_blocks))
            st.rerun()
