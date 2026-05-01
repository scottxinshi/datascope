import os
import chromadb
from chromadb.utils import embedding_functions

# Use ChromaDB's built-in embedding function (uses ONNX, no PyTorch needed)
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Create ChromaDB client
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(
    name="business_docs",
    embedding_function=embedding_fn
)

def chunk_text(text, chunk_size=200):
    """Split text into smaller chunks"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1
        if current_size >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def ingest_document(filepath):
    """Read a document, chunk it, and store in ChromaDB"""
    filename = os.path.basename(filepath)
    print(f"Ingesting {filename}...")

    with open(filepath, 'r') as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"  Split into {len(chunks)} chunks")

    # ChromaDB computes embeddings automatically
    for i, chunk in enumerate(chunks):
        collection.add(
            ids=[f"{filename}_chunk_{i}"],
            documents=[chunk],
            metadatas=[{"source": filename}]
        )
    print(f"  Done!")

if __name__ == "__main__":
    docs_folder = "docs"
    for filename in os.listdir(docs_folder):
        if filename.endswith(".txt"):
            ingest_document(os.path.join(docs_folder, filename))

    print(f"\nAll documents ingested! Total chunks stored: {collection.count()}")