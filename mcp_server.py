import os
import sys

# Make sure Python can find your agents
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from agents.sql_agent import ask as sql_ask
from agents.rag_agent import answer_from_docs as rag_ask

# Create the MCP server
mcp = FastMCP("DataScope")


@mcp.tool()
def run_database_query(question: str) -> str:
    """
    Answer a data question by querying the Northwind database.
    Use for questions about orders, customers, products, revenue,
    counts, quantities, and any data aggregation.
    """
    return sql_ask(question, silent=True)


@mcp.tool()
def search_business_documents(query: str) -> str:
    """
    Search business documents for policies, shipping rules,
    return procedures, product certifications, and product attributes
    like gluten-free or organic labels.
    """
    return rag_ask(query)


if __name__ == "__main__":
    mcp.run()