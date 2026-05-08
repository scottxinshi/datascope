import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.orchestrator import ask , decide_route
from agents.rag_agent import answer_from_docs, answer_from_docs_stream
from agents.sql_agent import ask as sql_ask
import io

# Page setup
st.set_page_config(page_title="DataScope", page_icon="🔍", layout="centered")
st.title("🔍 DataScope")
st.caption("Built by Scott Xin Shi")

# Add LinkedIn link in the sidebar
# with st.sidebar:
#     st.markdown("### 👋 About")
#     st.markdown("**DataScope** is a multi-agent AI analytics system that answers natural language questions about business data and documents.")
#     st.markdown("**Built by:** Scott Xin Shi")
#     st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/scott-xin-shi)")
#     st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-datascope-blue?logo=github)](https://github.com/scottxinshi/datascope)")
#     st.divider()
#     st.markdown("**Agents:**")
#     st.markdown("🗄️ SQL Agent — answers from data")
#     st.markdown("📄 RAG Agent — answers from documents")

# ****************************************

# Custom CSS that works for BOTH Light and Dark themes
st.markdown("""
    <style>
    /* Use 'rgba' for backgrounds so they tint based on the theme */
    .sidebar-card {
        background-color: rgba(255, 255, 255, 0.05); /* Very subtle overlay */
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
    }

    /* Apple-style muted text that works in dark/light */
    .secondary-text {
        color: #86868b;
        font-size: 0.85rem;
        line-height: 1.4;
    }

    /* Bold headers that pop */
    .card-header {
        font-weight: 600;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Smooth out the sidebar dividers */
    hr {
        margin: 1em 0px !important;
        opacity: 0.2 !important;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👋 About")
    
    # Description Card
    st.markdown("""
    <div class="sidebar-card">
        <div style="font-size: 0.9rem;">
            <b>DataScope</b> is a multi-agent AI analytics system that answers natural language questions about business data and documents.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Author & Socials Section
    st.markdown(f"""
    <div style="padding-left: 5px; margin-bottom: 20px;">
        <p class="secondary-text" style="font-weight: 600; font-size: 0.7rem; letter-spacing: 0.05em;">BUILT BY SCOTT XIN SHI</p>
        <div style="display: flex; gap: 10px; margin-top: 8px;">
            <a href="https://www.linkedin.com/in/scott-xin-shi" target="_blank"><img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin"></a>
            <a href="https://github.com/scottxinshi/datascope" target="_blank"><img src="https://img.shields.io/badge/GitHub-Project-717171?style=flat&logo=github"></a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("### 🤖 Agents")
    
    # SQL Agent Card
    st.markdown("""
    <div class="sidebar-card">
        <div class="card-header">🗄️ SQL Agent</div>
        <div class="secondary-text">Structured answers queried directly from your databases.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # RAG Agent Card
    st.markdown("""
    <div class="sidebar-card">
        <div class="card-header">📄 RAG Agent</div>
        <div class="secondary-text">Contextual insights extracted from uploaded documents.</div>
    </div>
    """, unsafe_allow_html=True)

# ****************************************

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

        # Spinner covers only the routing decision (invisible to user, ~1s LLM call)
        with st.spinner("Thinking..."):
            route = decide_route(prompt)

        st.caption(f"Routed to: {route} Agent")

        if route == "SQL":
            from agents.sql_agent import get_conn, generate_sql, run_sql, explain_results_stream
            conn = get_conn()
            schema = """
            orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
            products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
            customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
            """
            with st.spinner("Generating SQL..."):
                sql = generate_sql(prompt, schema)
            st.code(sql, language="sql")

            result, error = run_sql(conn, sql)
            if error:
                answer = f"Error running query: {error}"
                st.error(answer)
            else:
                st.dataframe(result)
                st.markdown("**Insight:**")
                answer = st.write_stream(explain_results_stream(prompt, sql, result.to_string(index=False)))

        elif route == "RAG":
            answer = st.write_stream(answer_from_docs_stream(prompt))

        else:  # NEITHER      added on 2026-05-06
            answer = (
                "I can only answer questions about business data and documents. "
                "Try asking about orders, customers, products, or company policies."
            )
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})