import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load CSV files into DuckDB as tables
def load_data():
    conn = duckdb.connect()
    conn.execute("CREATE TABLE orders AS SELECT * FROM read_csv_auto('data/orders.csv')")
    conn.execute("CREATE TABLE products AS SELECT * FROM read_csv_auto('data/products.csv')")
    conn.execute("CREATE TABLE customers AS SELECT * FROM read_csv_auto('data/customers.csv')")
    return conn

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
# One shot to LLM calls below: 
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
def ask(question):
    # Load data
    conn = load_data()
    
    # Describe the schema so the LLM knows what tables/columns exist
    schema = """
    orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
    products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
    customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
    """
    
    # Generate SQL from the question
    print(f"\nQuestion: {question}")
    sql = generate_sql(question, schema)
    print(f"Generated SQL: {sql}")
    
    # Run the SQL
    result, error = run_sql(conn, sql)
    
    # if error:
    #     print(f"Error: {error}")
    # else:
    #     print(f"\nResult:")
    #     print(result.to_string(index=False))

    if error:
        print(f"Error: {error}")
    else:
        print(f"\nResult:")
        print(result.to_string(index=False))
        
        # New: explain the results in plain English
        explanation = explain_results(question, sql, result.to_string(index=False))
        print(f"\nInsight: {explanation}")

# Test
if __name__ == "__main__":
    # ask("Which country has the most orders?")
    # ask("What are the top 3 most expensive products?")
    ask("Which customers are from Germany?")