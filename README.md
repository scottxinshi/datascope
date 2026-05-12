# 🔍 DataScope

A production-grade multi-agent AI analytics system that answers natural language questions about business data, documents, and the web.

Built by [Scott Xin Shi](https://www.linkedin.com/in/scott-xin-shi) · [GitHub](https://github.com/scottxinshi/datascope)

---

## What It Does

DataScope lets you ask questions in plain English and get answers from three sources:

- **Your database** — "Which country has the most orders?" → generates SQL, runs it, explains the result
- **Your documents** — "What is the return policy?" → searches PDFs, Word files, and text documents and returns a cited answer
- **The web** — "How many teams are in the 2026 FIFA World Cup?" → searches live web results and returns a cited answer

Every question is automatically routed to the right agent by an LLM-based orchestrator.

---

## Architecture

```
User Question
      ↓
Orchestrator (LangGraph + Llama 3.3 70B)
      ↓          ↓           ↓          ↓
SQL Agent    RAG Agent   Web Agent   Fallback
(DuckDB)  (ChromaDB)   (Tavily)    (NEITHER)
      ↓          ↓           ↓
Plain English Answer + Source Citation
      ↓
Confidence Score (🟢 High / 🟡 Medium / 🔴 Low)
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Llama 3.3 70B via Groq | AI reasoning — free, 280 tokens/sec |
| Orchestrator | LangGraph | Multi-agent graph routing |
| SQL Agent | Python + DuckDB | Natural language → SQL → explanation |
| RAG Agent | ChromaDB + ONNX embeddings | Document search with citations |
| Web Agent | Tavily Search API | Live web search with usage limit |
| Document Ingestion | pdfplumber + python-docx | Supports .txt, .pdf, .docx |
| MCP Server | FastMCP | Exposes tools to Claude Desktop and Cursor |
| API | FastAPI + Uvicorn | REST endpoint with Swagger UI |
| UI | Streamlit | Chat interface in the browser |
| LLMOps | MLflow | Tracks latency, tokens, and cost per call |
| Containers | Docker + Compose | Runs the full stack with one command |
| CI/CD | GitHub Actions | Auto-tests and builds on every push |

---

## Features

- **Multi-agent orchestration** — LangGraph graph routes questions to the right agent automatically
- **SQL Agent** — schema injection, two-step LLM pipeline, error handling, singleton connection for performance
- **RAG Agent** — vector similarity search, hallucination prevention, source citations
- **Web Agent** — live web search via Tavily with a 999-search monthly usage limit and automatic monthly reset
- **Conversation memory** — windowed memory keeps the last 3 turns of context so follow-up questions like "tell me more about those customers" reference previous answers
- **Evaluation pipeline** — golden dataset of 12 curated questions with LLM-as-judge scoring; tracks routing accuracy and answer accuracy to catch regressions
- **Agent confidence scoring** — every answer shows a confidence indicator (🟢 High / 🟡 Medium / 🔴 Low) based on observable signals: SQL result size, RAG chunk matches, and web source count
- **Expanded knowledge base** — 6 tables (orders, products, customers, employees, suppliers, order_details) enabling complex cross-table JOIN queries
- **Streaming responses** — tokens stream live to the UI as they are generated, no waiting for full response
- **Graceful degradation** — NEITHER route handles out-of-scope questions; empty SQL results return helpful messages instead of blank tables
- **Multi-format document ingestion** — ingest `.txt`, `.pdf`, and `.docx` files
- **MCP server** — connect Claude Desktop or Cursor to DataScope with zero extra code
- **FastAPI REST API** — with auto-generated Swagger UI at `/docs`
- **Streamlit chat UI** — session state, routing display, SQL + dataframe view, streaming output
- **MLflow LLMOps** — tracks every LLM call (latency, tokens, estimated cost)
- **Dockerized** — full stack runs anywhere with `docker-compose up`
- **CI/CD** — GitHub Actions runs tests and builds Docker on every push

---

## Quick Start

### Prerequisites
- Python 3.11
- Docker Desktop
- Free [Groq API key](https://console.groq.com)

### Run with Docker (recommended)

```bash
git clone https://github.com/scottxinshi/datascope.git
cd datascope

# Add your API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Start everything
docker-compose up
```

- Streamlit UI → http://localhost:8501
- FastAPI → http://localhost:8000/docs

### Run without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ingest documents
python3 pipelines/ingest_documents.py

# Start API
uvicorn api.main:app --reload

# Start UI (new terminal)
streamlit run ui/app.py
```

---

## MCP Server

DataScope exposes two tools via the Model Context Protocol (MCP), compatible with Claude Desktop and Cursor.

**Tools:**
- `run_database_query` — answers data questions using SQL
- `search_business_documents` — searches ingested documents

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "datascope": {
      "command": "/path/to/datascope/.venv/bin/python3",
      "args": ["/path/to/datascope/mcp_server.py"]
    }
  }
}
```

**Cursor config** (`.cursor/mcp.json` in project root):

```json
{
  "mcpServers": {
    "datascope": {
      "command": "/path/to/datascope/.venv/bin/python3",
      "args": ["/path/to/datascope/mcp_server.py"]
    }
  }
}
```

---

## Adding Your Own Documents

Drop any `.txt`, `.pdf`, or `.docx` file into the `docs/` folder, then run:

```bash
python3 pipelines/ingest_documents.py
```

The RAG agent will immediately start answering questions from the new document.

---

## Project Structure

```
datascope/
├── agents/
│   ├── orchestrator.py      # LangGraph multi-agent router
│   ├── sql_agent.py         # Natural language → SQL → explanation
│   ├── rag_agent.py         # Document search with citations
│   └── web_agent.py         # Live web search via Tavily with usage limit
├── api/
│   └── main.py              # FastAPI REST endpoints
├── ui/
│   └── app.py               # Streamlit chat interface
├── pipelines/
│   └── ingest_documents.py  # Ingests .txt, .pdf, .docx into ChromaDB
├── llmops/
│   └── tracker.py           # MLflow tracking
├── tests/
│   └── test_agents.py       # Pytest test suite
├── docs/                    # Drop documents here for RAG ingestion
├── data/                    # CSV datasets (Northwind)
├── mcp_server.py            # MCP server for Claude Desktop / Cursor
├── Dockerfile.api
├── Dockerfile.ui
├── docker-compose.yml
└── .github/workflows/ci.yml # GitHub Actions CI pipeline
```

---

## Environment Variables

```bash
# .env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

---

## Running Tests

```bash
pytest tests/test_agents.py -v
```

## Evaluation Pipeline

DataScope includes an evaluation pipeline that measures routing and answer accuracy against a golden dataset of 12 curated questions using LLM-as-judge scoring.

```bash
python tests/eval_pipeline.py
```

Results are saved to `data/eval_report.json`. Re-run after any major change (prompt updates, model swaps, new agents) to catch regressions.

Current baseline: **100% routing accuracy, 100% answer accuracy (12/12)**

---

## Tech Stack

Python · LangGraph · Groq API · Llama 3.3 70B · DuckDB · ChromaDB · Tavily · FastAPI · Streamlit · MLflow · Docker · GitHub Actions · MCP (Model Context Protocol)

---

## Roadmap

- [x] Streaming responses
- [x] Web search agent (Tavily)
- [x] Conversation memory
- [x] Evaluation pipeline with golden dataset
- [x] Automated eval on CI/CD (GitHub Actions)
- [x] Expanded knowledge base with cross-table JOIN support
- [x] Agent confidence scoring

---

*Built as a portfolio project to demonstrate AI engineering skills: multi-agent systems, RAG, LLMOps, MCP, REST APIs, and containerization.*
