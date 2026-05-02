import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sql_agent import load_data, generate_sql, run_sql

def test_load_data():
    """Test that the database loads correctly"""
    conn = load_data()
    assert conn is not None

def test_sql_generation_returns_string():
    """Test that SQL agent returns a string query"""
    schema = """
    orders(orderID, customerID, shipCountry)
    products(productID, productName, unitPrice)
    customers(customerID, companyName, country)
    """
    sql = generate_sql("Which country has the most orders?", schema)
    assert isinstance(sql, str)
    assert len(sql) > 0

def test_sql_execution():
    """Test that generated SQL runs without errors"""
    conn = load_data()
    schema = """
    orders(orderID, customerID, shipCountry)
    products(productID, productName, unitPrice)
    customers(customerID, companyName, country)
    """
    sql = generate_sql("What are the top 3 most expensive products?", schema)
    result, error = run_sql(conn, sql)
    assert error is None
    assert result is not None