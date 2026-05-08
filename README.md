# 🔍 DataScope

A production-grade multi-agent AI analytics system that answers natural language questions about business data and documents.

Built by [Scott Xin Shi](https://www.linkedin.com/in/scott-xin-shi) · [GitHub](https://github.com/scottxinshi/datascope)

---

## What It Does

DataScope lets you ask questions in plain English and get answers from two sources:

- **Your database** — "Which country has the most orders?" → generates SQL, runs it, explains the result
- **Your documents** — "What is the return policy?" → searches PDFs, Word files, and text documents and returns a cited answer

Every question is automatically routed to the right agent by an LLM-based orchestrator.

---

## Architecture

```
User Question
      ↓
Orchestrator (LangGraph + Llama 3.3 70B)
      ↓              ↓
SQL Agent         RAG Agent
(DuckDB)       (ChromaDB + ONNX)
      ↓              ↓
Plain English Answer + Source Citation
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Llama 3.3 70B via Groq | AI reasoning — free, 280 tokens/sec |
| Orchestrator | LangGraph | Multi-agent graph routing |
| SQL Agent | Python + DuckDB | Natural language → SQL → explanation |
| RAG Agent | ChromaDB + ONNX embeddings | Document search with citations |
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
│   └── rag_agent.py         # Document search with citations
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
```

---

## Running Tests

```bash
pytest tests/test_agents.py -v
```

---

## Tech Stack

Python · LangGraph · Groq API · Llama 3.3 70B · DuckDB · ChromaDB · FastAPI · Streamlit · MLflow · Docker · GitHub Actions · MCP (Model Context Protocol)

---

## Roadmap

- [x] Streaming responses
- [ ] Conversation memory
- [ ] Web search agent (third route)
- [ ] Evaluation pipeline with golden dataset
- [ ] Azure Container Apps deployment
- [ ] Authentication and row-level security

---

*Built as a portfolio project to demonstrate AI engineering skills: multi-agent systems, RAG, LLMOps, MCP, REST APIs, and containerization.*
