# app/review_pipeline.py
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from app.docx_utils import extract_text_from_docx, save_marked_docx
import json
import ollama  # If TinyLlama is run via Ollama
from typing import List, Dict
from pathlib import Path

# Required checklists
CHECKLISTS = {
    "Company Incorporation": [
        "Articles of Association",
        "Memorandum of Association",
        "Board Resolution",
        "UBO Declaration Form",
        "Register of Members and Directors"
    ]
}

def classify_doc_by_text(text: str) -> str:
    t = text.lower()
    if "article" in t and "association" in t:
        return "Articles of Association"
    if "memorandum" in t:
        return "Memorandum of Association"
    if "ubo" in t or "ultimate beneficial" in t:
        return "UBO Declaration Form"
    if "register of members" in t or "register of directors" in t:
        return "Register of Members and Directors"
    if "resolution" in t and ("board" in t or "shareholder" in t):
        return "Board Resolution"
    return "Unknown"

def get_retriever(persist_dir="adgm_chromadb", k=3):
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=persist_dir, embedding_function=emb)
    return db.as_retriever(search_kwargs={"k": k})

def build_prompt_for_review(doc_text: str, context_chunks: List[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    prompt = f"""
You are an ADGM compliance checker. Use the ADGM reference information below to identify compliance issues.

ADGM reference snippets:
{context}

Document to review:
{doc_text[:4500]}

Return ONLY JSON with this structure:
{{
  "document_name": "<exact name>",
  "issues_found": [
    {{
      "section": "Clause number or location",
      "issue": "Description of the red flag",
      "severity": "Low/Medium/High",
      "suggestion": "Suggested fix or clause change",
      "match_text": "Exact phrase or keyword in the document that triggered the flag"
    }}
  ],
  "citations": ["Relevant ADGM regulation or guideline reference"]
}}
"""
    return prompt

def call_tinyllama(prompt: str, model_name="tinyllama", max_tokens=1024):
    resp = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    return resp.get("message", {}).get("content", "")

def parse_json_from_model(output: str):
    try:
        start = output.find('{')
        end = output.rfind('}')
        if start != -1 and end != -1:
            return json.loads(output[start:end+1])
    except Exception as e:
        print("Failed parsing JSON:", e)
    return None

def review_single_docx(path: str, retriever, model_name="tinyllama"):
    text = extract_text_from_docx(path)
    
    # Retrieve relevant ADGM rules
    docs = retriever.get_relevant_documents(text[:1000])
    context_chunks = [d.page_content for d in docs]
    
    # LLM call
    prompt = build_prompt_for_review(text, context_chunks)
    raw_output = call_tinyllama(prompt, model_name=model_name)
    parsed = parse_json_from_model(raw_output) or {
        "document_name": Path(path).name,
        "issues_found": [],
        "citations": []
    }
    
    # Count red flags
    num_flags = len(parsed.get("issues_found", []))
    parsed["num_red_flags"] = num_flags  # <-- New field
    
    # Mark docx
    marks = []
    for issue in parsed["issues_found"]:
        marks.append({
            "match_text": issue.get("match_text", ""),
            "comment": f"{issue.get('issue')} — Suggestion: {issue.get('suggestion')}",
            "severity": issue.get("severity", "Info")
        })
    out_path = str(Path("examples") / f"reviewed_{Path(path).name}")
    save_marked_docx(path, marks, out_path)
    
    return parsed, out_path

def detect_overall_process(uploaded_doc_types: List[str]) -> Dict:
    best_process = None
    best_count = -1
    for process, reqs in CHECKLISTS.items():
        count = sum(1 for doc in uploaded_doc_types if doc in reqs)
        if count > best_count:
            best_count = count
            best_process = process
    required = CHECKLISTS.get(best_process, [])
    missing = [r for r in required if r not in uploaded_doc_types]
    return {
        "process": best_process,
        "documents_uploaded": len(uploaded_doc_types),
        "required_documents": len(required),
        "missing_documents": missing
    }
