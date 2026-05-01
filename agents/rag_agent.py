import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection(
    name="business_docs",
    embedding_function=embedding_fn
)

def search_documents(question, n_results=3): # 3- 5 normally
    """Find the most relevant chunks for a question"""
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )
    return results['documents'][0], results['metadatas'][0]

def answer_from_docs(question):
    """Search documents and answer the question with citations"""
    chunks, metadatas = search_documents(question)

    # Build context from retrieved chunks
    context = ""
    for i, (chunk, meta) in enumerate(zip(chunks, metadatas)):
        context += f"[Source: {meta['source']}]\n{chunk}\n\n"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a helpful assistant. Answer the question using ONLY 
the provided context. Always mention which document your answer comes from.
If the answer is not in the context, say 'I don't have that information in my documents.'"""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    questions = [
        "What is the return policy?",
        "How long does international shipping take?",
        "Which products are gluten-free?"
    ]

    for question in questions:
        print(f"\nQ: {question}")
        print(f"A: {answer_from_docs(question)}")
        print("-" * 50)