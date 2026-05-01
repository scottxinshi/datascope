import os
from dotenv import load_dotenv
from groq import Groq
from agents.sql_agent import ask as sql_ask
from agents.rag_agent import answer_from_docs as rag_ask

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def decide_route(question):
    """Ask the LLM to decide which agent should handle this question"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a routing assistant. Decide whether a question should be answered by:
- SQL: questions needing data aggregation, counts, filters on orders, customers, revenue, quantities, prices
- RAG: questions about policies, rules, shipping times, returns, product labels, certifications, guides

Key rule: if the question asks about a product ATTRIBUTE or LABEL (like gluten-free, organic, certified),
route to RAG — that information lives in documents, not the database.

Reply with ONLY one word: either SQL or RAG. Nothing else."""
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )
    return response.choices[0].message.content.strip().upper()

def ask(question):
    """Route the question to the right agent and return the answer"""
    print(f"\nQuestion: {question}")
    
    # Step 1: decide which agent to use
    route = decide_route(question)
    print(f"Routing to: {route} Agent")
    print("-" * 50)
    
    # Step 2: call the right agent
    if route == "SQL":
        sql_ask(question)
    elif route == "RAG":
        answer = rag_ask(question)
        print(f"Answer: {answer}")
    else:
        print("Could not determine the right agent for this question.")

if __name__ == "__main__":
    questions = [
        "Which country has the most orders?",
        "What is the return policy?",
        "What are the top 3 most expensive products?",
        "How long does international shipping take?",
        "Which customers are from Germany?",
        "What products are gluten-free?"
    ]

    for question in questions:
        ask(question)
        print("=" * 50)