"""
backend/chatbot.py
==================
Gemini-powered stock market chatbot.
Handles general Indian stock market questions.
"""
import os
import json
from google import genai
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL= "gemini-2.5-flash"

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


SYSTEM_PROMPT = """You are Market Pulse AI, an expert assistant for Indian stock markets (NSE/BSE).

You can help with:
- Stock prices, trends, and analysis
- Sector performance and market outlook
- IPOs, dividends, and corporate actions
- Trading strategies and risk management
- Explaining financial terms and concepts
- Comparing stocks and sectors
- General investing advice for Indian markets

Rules:
- Always use ₹ for Indian Rupee
- Keep answers concise and clear (under 150 words unless detail is asked)
- Always mention this is for informational purposes only, not financial advice
- If asked about a specific stock price, clarify you don't have real-time data
- Be friendly and professional
"""


def get_chat_response(message: str, history: list) -> str:
    """
    Get a response from Gemini for the chat message.
    
    history: list of {"role": "user"|"model", "text": "..."}
    """
    client = _get_client()

    # Build contents array with system prompt injected as first exchange
    contents = [
        {"role": "user",  "parts": [{"text": SYSTEM_PROMPT}]},
        {"role": "model", "parts": [{"text": "Understood! I'm Market Pulse AI, ready to help with Indian stock market questions."}]},
    ]

    # Add conversation history
    for h in history[-10:]:  # last 10 messages for context
        contents.append({
            "role":  h["role"],
            "parts": [{"text": h["text"]}]
        })

    # Add current message
    contents.append({
        "role":  "user",
        "parts": [{"text": message}]
    })

    try:
        response = _get_client().models.generate_content(
            model=MODEL,
            contents=contents,
        )
        return response.text.strip()
    except Exception as e:
        return f"Sorry, I couldn't process that: {str(e)}"