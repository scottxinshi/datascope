import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load CSV files into DuckDB as tables

# relative path fixed on 2026-05-04
# def load_data():
#     conn = duckdb.connect()
#     conn.execute("CREATE TABLE orders AS SELECT * FROM read_csv_auto('data/orders.csv')")
#     conn.execute("CREATE TABLE products AS SELECT * FROM read_csv_auto('data/products.csv')")
#     conn.execute("CREATE TABLE customers AS SELECT * FROM read_csv_auto('data/customers.csv')")
#     return conn
def load_data():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    conn = duckdb.connect()
    conn.execute(f"CREATE TABLE orders AS SELECT * FROM read_csv_auto('{BASE_DIR}/data/orders.csv')")
    conn.execute(f"CREATE TABLE products AS SELECT * FROM read_csv_auto('{BASE_DIR}/data/products.csv')")
    conn.execute(f"CREATE TABLE customers AS SELECT * FROM read_csv_auto('{BASE_DIR}/data/customers.csv')")
    return conn

# Singleton connection — load CSV data once at module startup, reuse for all calls
# Performance fix on 2026-05-07: previously load_data() was called on every ask(),
# re-reading CSV files and recreating tables each time. Now it loads once and reuses.
_conn = None

def get_conn():
    global _conn
    if _conn is None:
        _conn = load_data()
    return _conn

# Ask the LLM to generate SQL for a question
def generate_sql(question, schema):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are a SQL expert. Generate a DuckDB SQL query to answer the user's question.
                
Database schema:
{schema}

Rules:
- Return ONLY the SQL query, nothing else
- No explanations, no markdown, no backticks
- Use only the tables and columns in the schema above"""
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )
    return response.choices[0].message.content.strip()

# ***********************************************************
# ***********************************************************
# One shot two LLM calls below: 
# First LLM call — generated the SQL query
# Second LLM call — explained the results in plain English

# Run the SQL and return results
def run_sql(conn, sql):
    try:
        result = conn.execute(sql).df()  # .df() converts to pandas DataFrame
        return result, None
    except Exception as e:
        return None, str(e)
    
# Added Explain Results so explain it in plain English
def explain_results(question, sql, results):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful data analyst. Explain query results in clear, concise plain English. Be specific with numbers. Keep it to 2-3 sentences."
            },
            {
                "role": "user",
                "content": f"""Question asked: {question}
                
SQL that was run: {sql}

Results: {results}

Please explain these results clearly."""
            }
        ]
    )
    return response.choices[0].message.content.strip()
# ***********************************************************
# ***********************************************************


# Main function that puts it all together
def ask(question, silent=False):
    conn = get_conn()
    
    schema = """
    orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
    products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
    customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
    """
    
    if not silent:
        print(f"\nQuestion: {question}")
    sql = generate_sql(question, schema)
    if not silent:
        print(f"Generated SQL: {sql}")
    
    result, error = run_sql(conn, sql)

    if error:
        if not silent:
            print(f"Error: {error}")
        return f"Sorry, I couldn't run that query. Error: {error}"
    # else:
    #     if not silent:
    #         print(f"\nResult:")
    #         print(result.to_string(index=False))
        
    #     explanation = explain_results(question, sql, result.to_string(index=False))
    #     if not silent:
    #         print(f"\nInsight: {explanation}")
    #     return explanation  # added on 2026-05-04 to avoid "NoneType"
    else:
        if result.empty:
            if not silent:
                print("No results found.")
            return "I don't have data to answer that question. The query returned no results — try asking about orders, customers, or products in the database."
        
        if not silent:
            print(f"\nResult:")
            print(result.to_string(index=False))
        
        explanation = explain_results(question, sql, result.to_string(index=False))
        if not silent:
            print(f"\nInsight: {explanation}")
        return explanation

# Test
if __name__ == "__main__":
    # ask("Which country has the most orders?")
    # ask("What are the top 3 most expensive products?")
    ask("Which customers are from Germany?")