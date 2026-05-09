import os
import json
from datetime import datetime
from tavily import TavilyClient
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE_FILE = os.path.join(BASE_DIR, "data", "search_usage.json")
MONTHLY_LIMIT = 999 #1000 is the maximum free credit in Tavily; I'll leave 1 buffer as my defensive coding


def load_usage():
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def check_and_increment():
    """Returns True if search is allowed, False if limit reached."""
    usage = load_usage()
    current_month = datetime.now().strftime("%Y-%m")

    # Reset counter if it's a new month
    if usage["month"] != current_month:
        usage = {"month": current_month, "count": 0}

    if usage["count"] >= MONTHLY_LIMIT:
        return False

    usage["count"] += 1
    save_usage(usage)
    return True


def get_remaining_searches():
    usage = load_usage()
    current_month = datetime.now().strftime("%Y-%m")
    if usage["month"] != current_month:
        return MONTHLY_LIMIT
    return max(0, MONTHLY_LIMIT - usage["count"])


def search_web(question):
    """Search the web and return an answer. Returns None if limit reached."""
    if not check_and_increment():
        remaining = get_remaining_searches()
        return (
            f"Monthly web search limit of {MONTHLY_LIMIT} reached. "
            f"Resets on the 1st of next month. "
            f"Try asking about your business data or documents instead."
        )

    try:
        results = tavily.search(query=question, max_results=5)
        sources = results.get("results", [])

        context = ""
        for i, source in enumerate(sources):
            context += f"[Source {i+1}: {source['url']}]\n{source['content']}\n\n"

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful research assistant. Answer the question using the provided web search results.
Always cite your sources by mentioning the URL. Keep the answer concise and factual."""
                },
                {
                    "role": "user",
                    "content": f"Search results:\n{context}\n\nQuestion: {question}"
                }
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            return "Monthly web search limit reached. Resets on the 1st of next month."
        return f"Web search failed: {str(e)}"


def search_web_stream(question):
    """Streaming version of search_web — yields tokens as they arrive."""
    if not check_and_increment():
        yield (
            f"Monthly web search limit of {MONTHLY_LIMIT} reached. "
            f"Resets on the 1st of next month. "
            f"Try asking about your business data or documents instead."
        )
        return

    try:
        results = tavily.search(query=question, max_results=5)
        sources = results.get("results", [])

        context = ""
        for i, source in enumerate(sources):
            context += f"[Source {i+1}: {source['url']}]\n{source['content']}\n\n"

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful research assistant. Answer the question using the provided web search results.
Always cite your sources by mentioning the URL. Keep the answer concise and factual."""
                },
                {
                    "role": "user",
                    "content": f"Search results:\n{context}\n\nQuestion: {question}"
                }
            ],
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            yield "Monthly web search limit reached. Resets on the 1st of next month."
        else:
            yield f"Web search failed: {str(e)}"


if __name__ == "__main__":
    print(f"Searches remaining this month: {get_remaining_searches()}")
    print(search_web("What is the latest version of Python?"))
