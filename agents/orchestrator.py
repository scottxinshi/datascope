import os
import time
from typing import TypedDict, Literal

from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import StateGraph, END

from agents.sql_agent import ask as sql_ask
from agents.rag_agent import answer_from_docs as rag_ask
from llmops.tracker import track_llm_call

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── 1. State ──────────────────────────────────────────────────────────────────
# This dictionary flows through every node in the graph.
# Each node reads from it and writes back to it.

class AgentState(TypedDict):
    question: str
    route: str
    answer: str
    tokens_used: int


# ── 2. Nodes ──────────────────────────────────────────────────────────────────
# Each node is a function that receives the current state and returns updates.
def decide_route(question: str) -> str:
    """Return 'SQL' or 'RAG' for a given question. Used by the UI directly."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a routing assistant.
- SQL: questions needing data aggregation, counts, filters on orders,
  customers, revenue, quantities, prices
- RAG: questions about policies, rules, shipping times, returns,
  product labels, certifications, guides

Key rule: if the question asks about a product ATTRIBUTE or LABEL
(like gluten-free, organic), route to RAG.

Reply with ONLY one word: SQL or RAG."""
            },
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content.strip().upper()

# def orchestrator_node(state: AgentState) -> AgentState:
#     """Ask the LLM to decide: SQL or RAG?"""
#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {
#                 "role": "system",
#                 "content": """You are a routing assistant.
# - SQL: questions needing data aggregation, counts, filters on orders,
#   customers, revenue, quantities, prices
# - RAG: questions about policies, rules, shipping times, returns,
#   product labels, certifications, guides

# Key rule: if the question asks about a product ATTRIBUTE or LABEL
# (like gluten-free, organic), route to RAG.

# Reply with ONLY one word: SQL or RAG."""
#             },
#             {"role": "user", "content": state["question"]}
#         ]
#     )
#     route = response.choices[0].message.content.strip().upper()
#     tokens = response.usage.total_tokens
#     return {**state, "route": route, "tokens_used": tokens}
def orchestrator_node(state: AgentState) -> AgentState:
    """Ask the LLM to decide: SQL or RAG?"""
    route = decide_route(state["question"])
    # count tokens separately since decide_route doesn't return usage
    return {**state, "route": route, "tokens_used": 0}


def sql_node(state: AgentState) -> AgentState:
    """Run the SQL agent and store the answer in state."""
    answer = sql_ask(state["question"])
    return {**state, "answer": answer}


def rag_node(state: AgentState) -> AgentState:
    """Run the RAG agent and store the answer in state."""
    answer = rag_ask(state["question"])
    return {**state, "answer": answer}


# ── 3. Routing function ───────────────────────────────────────────────────────
# This function reads the route from state and tells the graph which node to go to next.

def route_decision(state: AgentState) -> Literal["sql_agent", "rag_agent"]:
    if state["route"] == "SQL":
        return "sql_agent"
    return "rag_agent"


# ── 4. Build the graph ────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)

workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("rag_agent", rag_node)

workflow.set_entry_point("orchestrator")

workflow.add_conditional_edges(
    "orchestrator",       # from this node
    route_decision,       # call this function to decide
    {
        "sql_agent": "sql_agent",   # if returns "sql_agent" → go to sql_agent node
        "rag_agent": "rag_agent",   # if returns "rag_agent" → go to rag_agent node
    }
)

workflow.add_edge("sql_agent", END)
workflow.add_edge("rag_agent", END)

graph = workflow.compile()


# ── 5. Public interface ───────────────────────────────────────────────────────
# Same function name and return value as before — api/main.py and ui/app.py unchanged.

def ask(question: str) -> tuple[str, str]:
    start_time = time.time()

    result = graph.invoke({
        "question": question,
        "route": "",
        "answer": "",
        "tokens_used": 0,
    })

    track_llm_call(
        question,
        result["route"],
        result["answer"],
        result["tokens_used"],
        start_time,
    )

    return result["route"], result["answer"]




# import os
# import time
# from dotenv import load_dotenv
# from groq import Groq
# from agents.sql_agent import ask as sql_ask
# from agents.rag_agent import answer_from_docs as rag_ask
# from llmops.tracker import track_llm_call

# load_dotenv()

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# def decide_route(question):
#     """Ask the LLM to decide which agent should handle this question"""
#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {
#                 "role": "system",
#                 "content": """You are a routing assistant. Decide whether a question should be answered by:
# - SQL: questions needing data aggregation, counts, filters on orders, customers, revenue, quantities, prices
# - RAG: questions about policies, rules, shipping times, returns, product labels, certifications, guides

# Key rule: if the question asks about a product ATTRIBUTE or LABEL (like gluten-free, organic, certified),
# route to RAG — that information lives in documents, not the database.

# Reply with ONLY one word: either SQL or RAG. Nothing else."""
#             },
#             {
#                 "role": "user",
#                 "content": question
#             }
#         ]
#     )
#     return response.choices[0].message.content.strip().upper()

# def ask(question):
#     """Route the question to the right agent and return the answer"""
#     start_time = time.time()
    
#     print(f"\nQuestion: {question}")
#     route = decide_route(question)
#     print(f"Routing to: {route} Agent")
#     print("-" * 50)

#     tokens_used = 0
#     answer = ""

#     if route == "SQL":
#         from agents.sql_agent import load_data, generate_sql, run_sql, explain_results
#         conn = load_data()
#         schema = """
#         orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
#         products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
#         customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
#         """
#         sql = generate_sql(question, schema)
#         result, error = run_sql(conn, sql)
#         if error:
#             answer = f"Error: {error}"
#         else:
#             answer = explain_results(question, sql, result.to_string(index=False))
#             tokens_used = len(question.split()) + len(answer.split())

#     elif route == "RAG":
#         answer = rag_ask(question)
#         tokens_used = len(question.split()) + len(answer.split())

#     # Track to MLflow
#     track_llm_call(question, route, answer, tokens_used, start_time)

#     return route, answer

# if __name__ == "__main__":
#     questions = [
#         "Which country has the most orders?",
#         "What is the return policy?",
#         "What are the top 3 most expensive products?",
#         "How long does international shipping take?",
#     ]

#     for question in questions:
#         ask(question)
#         print("=" * 50)