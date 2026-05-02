import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel
from agents.orchestrator import ask

# Create the FastAPI app
app = FastAPI(
    title="DataScope API",
    description="Multi-agent AI analytics system",
    version="1.0.0"
)

# Define what the request body looks like
class QuestionRequest(BaseModel):
    question: str

# Define what the response looks like
class QuestionResponse(BaseModel):
    question: str
    route: str
    answer: str

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Main endpoint
@app.post("/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest):
    route, answer = ask(request.question)
    return QuestionResponse(
        question=request.question,
        route=route,
        answer=answer
    )