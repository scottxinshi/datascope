import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.orchestrator import ask, decide_route
from agents.rag_agent import answer_from_docs
from agents.sql_agent import ask as sql_ask
import io

# Page setup
st.set_page_config(page_title="DataScope", page_icon="🔍", layout="centered")
st.title("🔍 DataScope")
st.caption("Built by Scott Xin Shi")

# Add LinkedIn link in the sidebar
with st.sidebar:
    st.markdown("### 👋 About")
    st.markdown("**DataScope** is a multi-agent AI analytics system that answers natural language questions about business data and documents.")
    st.markdown("**Built by:** Scott Xin Shi")
    st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/scott-xin-shi)")
    st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-datascope-blue?logo=github)](https://github.com/scottxinshi/datascope)")
    st.divider()
    st.markdown("**Agents:**")
    st.markdown("🗄️ SQL Agent — answers from data")
    st.markdown("📄 RAG Agent — answers from documents")

# Keep chat history across messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input box at the bottom
if prompt := st.chat_input("Ask a question..."):
    
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get answer from orchestrator
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            # Decide route
            route = decide_route(prompt)
            st.caption(f"Routed to: {route} Agent")
            
            if route == "SQL":
                # Capture SQL agent output
                from agents.sql_agent import load_data, generate_sql, run_sql, explain_results
                conn = load_data()
                schema = """
                orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
                products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
                customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
                """
                sql = generate_sql(prompt, schema)
                st.code(sql, language="sql")
                
                result, error = run_sql(conn, sql)
                if error:
                    answer = f"Error running query: {error}"
                    st.error(answer)
                else:
                    st.dataframe(result)
                    answer = explain_results(prompt, sql, result.to_string(index=False))
                    st.markdown(f"**Insight:** {answer}")
                    
            elif route == "RAG":
                answer = answer_from_docs(prompt)
                st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})