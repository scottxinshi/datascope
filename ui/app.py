import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.orchestrator import ask, decide_route
from agents.rag_agent import answer_from_docs, answer_from_docs_stream, search_documents, score_rag_confidence
from agents.web_agent import search_web_stream, get_remaining_searches, score_web_confidence
from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()
from agents.sql_agent import ask as sql_ask
import io
import time


def try_render_chart(df):
    """Auto-detect chart type from SQL result and render it."""
    if df is None or df.empty or len(df) < 2:
        return
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if not numeric_cols:
        return

    year_cols = [c for c in df.columns if 'year' in c.lower()]
    cat_cols = [c for c in df.columns if c in [
        'category', 'experience_level', 'employment_type',
        'company_location', 'country', 'remote_ratio'
    ]]

    if year_cols:
        idx = year_cols[0]
        value_cols = [c for c in numeric_cols if c != idx]  # exclude index col
        if not value_cols:
            return
        # category + year + one value → pivot into multi-line chart
        if cat_cols and len(value_cols) == 1:
            try:
                pivot = df.pivot(index=idx, columns=cat_cols[0], values=value_cols[0])
                st.line_chart(pivot)
                return
            except Exception:
                pass
        st.line_chart(df.set_index(idx)[value_cols])
    elif cat_cols and numeric_cols:
        st.bar_chart(df.set_index(cat_cols[0])[numeric_cols[:1]])
    elif len(df.columns) == 2 and len(numeric_cols) == 1:
        st.bar_chart(df.set_index(df.columns[0])[numeric_cols])

# Page setup
st.set_page_config(page_title="DataScope", page_icon="🔍", layout="centered")
st.title("DataScope")
st.caption("Built by Scott Xin Shi")

# Custom CSS that works for BOTH Light and Dark themes
st.markdown("""
    <style>
    .sidebar-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
    }
    .secondary-text {
        color: #86868b;
        font-size: 0.85rem;
        line-height: 1.4;
    }
    .card-header {
        font-weight: 600;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    hr {
        margin: 1em 0px !important;
        opacity: 0.2 !important;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### About")

    st.markdown("""
    <div class="sidebar-card">
        <div style="font-size: 0.9rem;">
            <b>DataScope</b> is a multi-agent AI analytics system that answers natural language questions about business data and documents.
        </div>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown("""
    <div class="sidebar-card">
        <div class="card-header">🗄️ SQL Agent</div>
        <div class="secondary-text">Structured answers from business data and the data industry job market (66K salary records, 2023–2025, US & Canada).</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-card">
        <div class="card-header">📄 RAG Agent</div>
        <div class="secondary-text">Contextual insights extracted from uploaded documents.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sidebar-card">
        <div class="card-header">🌐 Web Agent</div>
        <div class="secondary-text">Live answers from the web for general knowledge questions.</div>
        <div class="secondary-text" style="margin-top: 6px;">Searches remaining: <b>{get_remaining_searches()}</b> / 999</div>
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

        # Extract conversation history for context (last 3 turns = 6 messages)
        history = st.session_state.messages[-6:] if st.session_state.messages else []

        # Spinner covers only the routing decision
        start_time = time.time()
        with st.spinner("Thinking..."):
            route = decide_route(prompt)

        st.caption(f"Routed to: {route} Agent")

        if route == "SQL":
            from agents.sql_agent import get_conn, generate_sql, run_sql, explain_results_stream, score_sql_confidence
            conn = get_conn()
            schema = """
            -- Northwind business tables
            orders(orderID, customerID, employeeID, orderDate, requiredDate, shippedDate, shipVia, freight, shipName, shipAddress, shipCity, shipRegion, shipPostalCode, shipCountry)
            products(productID, productName, supplierID, categoryID, quantityPerUnit, unitPrice, unitsInStock, unitsOnOrder, reorderLevel, discontinued)
            customers(customerID, companyName, contactName, contactTitle, address, city, region, postalCode, country, phone, fax)
            employees(employeeID, lastName, firstName, title, titleOfCourtesy, birthDate, hireDate, city, region, country, reportsTo)
            suppliers(supplierID, companyName, contactName, contactTitle, city, region, country, phone)
            order_details(orderID, productID, unitPrice, quantity, discount)

            -- Data industry job market (aijobs.net, 2023-2025, US & Canada, 66,527 rows)
            -- Use salary_in_usd for all salary comparisons (already converted to USD)
            -- experience_level: EN=Entry, MI=Mid, SE=Senior, EX=Executive
            -- employment_type: FT=Full-time, CT=Contract, PT=Part-time, FL=Freelance
            -- remote_ratio: 0=On-site, 50=Hybrid, 100=Fully Remote
            -- company_location: US or CA (ISO country code)
            -- category values: 'Data Scientist', 'Data Engineer', 'Data Analyst', 'ML Engineer', 'AI Engineer'
            jobs(work_year, experience_level, employment_type, job_title, salary, salary_currency,
                 salary_in_usd, employee_residence, remote_ratio, company_location, company_size, category)
            """
            with st.spinner("Generating SQL..."):
                sql = generate_sql(prompt, schema)
            st.code(sql, language="sql")

            result, error = run_sql(conn, sql)
            confidence = score_sql_confidence(result, error)
            st.caption(f"Confidence: {confidence}")

            if error:
                answer = f"Error running query: {error}"
                st.error(answer)
            else:
                st.dataframe(result)
                try_render_chart(result)
                st.markdown("**Insight:**")
                answer = st.write_stream(explain_results_stream(prompt, sql, result.to_string(index=False), history=history))

        elif route == "RAG":
            chunks, _ = search_documents(prompt)
            confidence = score_rag_confidence(chunks)
            st.caption(f"Confidence: {confidence}")
            answer = st.write_stream(answer_from_docs_stream(prompt, history=history))

        elif route == "WEB":
            with st.spinner("Searching the web..."):
                tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                web_results = tavily_client.search(query=prompt, max_results=5)
                sources = web_results.get("results", [])
                confidence = score_web_confidence(sources)
            st.caption(f"Confidence: {confidence}")
            answer = st.write_stream(search_web_stream(prompt, history=history, prefetched_sources=sources))

        else:  # NEITHER
            answer = (
                "I can only answer questions about business data, documents, or general knowledge. "
                "Try asking about orders, customers, products, company policies, or current events."
            )
            st.markdown(answer)

        elapsed = time.time() - start_time
        st.caption(f"⏱ Answered in {elapsed:.1f}s")

    st.session_state.messages.append({"role": "assistant", "content": answer})
