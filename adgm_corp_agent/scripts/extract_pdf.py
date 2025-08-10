# scripts/extract_pdf.py
import fitz  # PyMuPDF
import re
from pathlib import Path

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    raw_text = "\n".join(pages)
    # Normalize spaces/newlines
    clean = re.sub(r'\n{2,}', '\n\n', raw_text).strip()
    return clean

def save_to_txt(pdf_path: str, out_txt: str):
    txt = extract_text_from_pdf(pdf_path)
    p = Path(out_txt)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    print(f"Saved extracted text to {out_txt}")

if __name__ == "__main__":
    import sys
    pdf = "data/Data Sources.pdf" if len(sys.argv) == 1 else sys.argv[1]
    out = "data/adgm_data_sources.txt"
    save_to_txt(pdf, out)
