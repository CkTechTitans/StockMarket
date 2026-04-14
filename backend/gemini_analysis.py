"""
backend/gemini_analysis.py
===========================
Gemini AI analysis using the NEW google-genai SDK.

Install: pip install google-genai
"""

import json
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

  # <- paste your key

MODEL = "gemini-3-flash-preview"   # latest fast model

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def analyze_stock(stock: dict, chart: list) -> dict:
    """
    Ask Gemini to analyse a stock given its quote + recent price history.
    Returns dict: recommendation, confidence, sentiment, score,
                  summary, reasons, risks, outlook, price_target.
    """
    client = _get_client()

    # Build price history block
    if chart:
        recent = chart[-10:]
        price_summary = "\n".join(
            f"  {d['date']}: O={d['open']:.2f} H={d['high']:.2f} "
            f"L={d['low']:.2f} C={d['close']:.2f} Vol={d['volume']:,}"
            for d in recent
        )
    else:
        price_summary = "No historical data available."

    prompt = f"""
You are a senior equity research analyst specializing in Indian stock markets (NSE/BSE).

Your job is to provide COMPLETE stock analysis like a professional brokerage report.

IMPORTANT:
- Respond ONLY in valid JSON
- No markdown, no explanation outside JSON
- Be specific, realistic, and data-driven (avoid generic statements)

Stock Data:
Symbol: {stock.get('symbol')}
Name: {stock.get('name')}
Current Price: Rs {stock.get('price')}
Day Change: {stock.get('change')} ({stock.get('change_pct')}%)
Open: Rs {stock.get('open')}
High: Rs {stock.get('high')}
Low: Rs {stock.get('low')}
Prev Close: Rs {stock.get('prev_close')}
Volume: {stock.get('volume')}
Date: {stock.get('date')}

Recent 10-Day Price History:
{price_summary}

Return EXACT JSON in this structure:

{{
  "recommendation": "BUY | SELL | HOLD",
  "confidence": "High | Medium | Low",
  "sentiment": "Bullish | Neutral | Bearish",
  "score": 1-10,

  "summary": "2-line professional market summary",

  "business": "What the company does and its strength in 1-2 lines",

  "financials": {{
    "trend": "Growing | Stable | Weak",
    "profitability": "Strong | متوسط | Weak",
    "comment": "Short explanation"
  }},

  "technical": {{
    "trend": "Uptrend | Sideways | Downtrend",
    "rsi_signal": "Overbought | Neutral | Oversold",
    "volume_trend": "Increasing | Decreasing | Stable"
  }},

  "levels": {{
    "support": "Rs XXX",
    "resistance": "Rs XXX"
  }},

  "valuation": {{
    "status": "Undervalued | Fair | Overvalued",
    "comment": "Short reasoning"
  }},

  "reasons": ["3 strong bullish/bearish reasons"],

  "risks": ["2-3 key risks"],

  "outlook": "2-line 3-month forward view",

  "action": "Clear actionable advice (e.g. Buy on dips, Avoid, Breakout buy)",

  "entry_zone": "Rs XXX - XXX",

  "price_target": "Rs XXX - XXX",

  "time_horizon": "Short-term | Medium-term | Long-term"

}}"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        text = response.text.strip()

        # Strip accidental markdown fences if any
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        return _error_result(f"JSON parse error: {e}")
    except Exception as e:
        return _error_result(str(e))


def _error_result(msg: str) -> dict:
    return {
        "recommendation": "N/A",
        "confidence": "N/A",
        "sentiment": "N/A",
        "score": 0,
        "summary": f"AI analysis unavailable: {msg}",
        "reasons": [],
        "risks": [],
        "outlook": "N/A",
        "price_target": "N/A",
    }


def chat_with_stocks(message: str, history: list, stocks: list) -> tuple:
    """
    Chatbot: answer user questions about their watchlist stocks.
    Returns (reply_text, suggestions_list)
    """
    try:
        model_name = _discover_model()
    except RuntimeError as e:
        return f"AI unavailable: {e}", []

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name)

    # Build stock context
    stock_context = ""
    for s in stocks:
        stock_context += (
            f"\n- {s.get('symbol')} ({s.get('name')}): "
            f"Price=₹{s.get('price')}, Change={s.get('change_pct')}%, "
            f"Open=₹{s.get('open')}, High=₹{s.get('high')}, "
            f"Low=₹{s.get('low')}, PrevClose=₹{s.get('prev_close')}, "
            f"Volume={s.get('volume')}"
        )

    # Build conversation history
    history_text = ""
    for h in history[-6:]:
        role = "User" if h.get("role") == "user" else "Assistant"
        history_text += f"\n{role}: {h.get('content','')}"

    prompt = f"""You are a friendly Indian stock market assistant helping a user understand their watchlist.
Be concise, factual, and helpful. Use ₹ for prices. Format numbers in Indian style (Cr, L).
If asked about a stock not in the watchlist, say you only have data for listed stocks.

Current Watchlist Data:{stock_context}

Conversation so far:{history_text}

User: {message}

Reply naturally and helpfully. At the end, suggest 2-3 short follow-up questions the user might ask, 
formatted as JSON after your reply like this:
SUGGESTIONS: ["question1", "question2", "question3"]"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Parse suggestions if present
        suggestions = []
        if "SUGGESTIONS:" in text:
            parts = text.split("SUGGESTIONS:", 1)
            reply = parts[0].strip()
            try:
                suggestions = json.loads(parts[1].strip())
            except Exception:
                suggestions = []
        else:
            reply = text

        return reply, suggestions
    except Exception as e:
        return f"Sorry, I encountered an error: {e}", []