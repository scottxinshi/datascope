import os
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

import pdfplumber
from docx import Document as DocxDocument

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Persistent Database
chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
embedding_fn = DefaultEmbeddingFunction()
# collection = chroma_client.get_or_create_collection(
#     name="documents",
#     embedding_function=embedding_fn
# )
collection = chroma_client.get_or_create_collection(
    name="business_docs",
    embedding_function=embedding_fn
)


def extract_text(filepath):
    """Extract text from .txt, .pdf, or .docx files."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, "r") as f:
            return f.read()

    elif ext == ".pdf":
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    elif ext == ".docx":
        doc = DocxDocument(filepath)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    else:
        print(f"Skipping unsupported file type: {ext}")
        return None


def chunk_text(text, chunk_size=200):
    """Split text into chunks of ~chunk_size characters."""
    words = text.split()
    chunks, current, length = [], [], 0
    for word in words:
        current.append(word)
        length += len(word) + 1
        if length >= chunk_size:
            chunks.append(" ".join(current))
            current, length = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_document(filepath):
    """Ingest a single document into ChromaDB."""
    text = extract_text(filepath)
    if not text:
        return

    filename = os.path.basename(filepath)
    chunks = chunk_text(text)

    # Remove existing chunks for this file to avoid duplicates
    existing = collection.get(where={"source": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": filename} for _ in chunks]

    collection.add(ids=ids, documents=chunks, metadatas=metadatas)
    print(f"✓ {filename} — {len(chunks)} chunks ingested")


def ingest_all():
    """Ingest all supported documents from the docs/ folder."""
    docs_dir = os.path.join(BASE_DIR, "docs")
    supported = {".txt", ".pdf", ".docx"}

    files = [f for f in os.listdir(docs_dir)
             if os.path.splitext(f)[1].lower() in supported]

    if not files:
        print("No supported files found in docs/")
        return

    print(f"Found {len(files)} documents to ingest...\n")
    for filename in files:
        ingest_document(os.path.join(docs_dir, filename))

    print(f"\nDone! {len(files)} documents ingested.")


if __name__ == "__main__":
    ingest_all()