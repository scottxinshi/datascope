import os
from dotenv import load_dotenv
from groq import Groq

# Read the .env file and load GROQ_API_KEY into memory
load_dotenv()

# Create the Groq client using the API key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Make your first LLM call
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Say hello and tell me what you are in one sentence."}
    ]
)

# Print the AI's response
print(response.choices[0].message.content)