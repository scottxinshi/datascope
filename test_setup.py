import os
from dotenv import load_dotenv
from groq import Groq

# Read the .env file and load GROQ_API_KEY into memory
load_dotenv()

# Create the Groq client using the API key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# Model is env-configurable so a provider deprecation is a .env change, not a code change.
# Groq decommissioned llama-3.3-70b-versatile on 2026-08-16.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# Make your first LLM call
response = client.chat.completions.create(
    model=GROQ_MODEL,
    messages=[
        {"role": "user", "content": "Say hello and tell me what you are in one sentence."}
    ]
)

# Print the AI's response
print(response.choices[0].message.content)