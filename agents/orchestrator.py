import os
import time
from dotenv import load_dotenv
from groq import Groq
from agents.sql_agent import ask as sql_ask
from agents.rag_agent import answer_from_docs as rag_ask
from llmops.tracker import track_llm_call

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
    start_time = time.time()
    
    print(f"\nQuestion: {question}")
    route = decide_route(question)
    print(f"Routing to: {route} Agent")
    print("-" * 50)

    tokens_used = 0
    answer = ""

    if route == "SQL":
        from agents.sql_agent import load_data, generate_sql, run_sql, explain_results
        conn = load_data()
        schema = """
        orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
        products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
        customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
        """
        sql = generate_sql(question, schema)
        result, error = run_sql(conn, sql)
        if error:
            answer = f"Error: {error}"
        else:
            answer = explain_results(question, sql, result.to_string(index=False))
            tokens_used = len(question.split()) + len(answer.split())

    elif route == "RAG":
        answer = rag_ask(question)
        tokens_used = len(question.split()) + len(answer.split())

    # Track to MLflow
    track_llm_call(question, route, answer, tokens_used, start_time)

    return route, answer

if __name__ == "__main__":
    questions = [
        "Which country has the most orders?",
        "What is the return policy?",
        "What are the top 3 most expensive products?",
        "How long does international shipping take?",
    ]

    for question in questions:
        ask(question)
        print("=" * 50)