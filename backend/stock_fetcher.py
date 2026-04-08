"""
backend/stock_fetcher.py
========================
Fetches Indian stock data using yfinance.
Uses fast_info + interval history for most real-time
data possible without a paid API.

Data freshness:
  Quotes   → fast_info: ~2-5 min delay (much faster than .info)
  1W chart → 15m candles
  1M+ chart→ daily candles

Install: pip install yfinance
"""

import time
import datetime
import yfinance as yf


def _safe_float(val, default=0.0) -> float:
    try:
        return round(float(val), 2) if val is not None else default
    except (TypeError, ValueError):
        return default


def _format_date(ts) -> str:
    if not ts:
        return datetime.date.today().isoformat()
    try:
        if isinstance(ts, (int, float)):
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        return str(ts)[:10]
    except Exception:
        return datetime.date.today().isoformat()


def _get_ticker(symbol: str):
    """Try NSE (.NS) first, then BSE (.BO). Returns (ticker, suffix)."""
    for suffix in [".NS", ".BO"]:
        try:
            ticker = yf.Ticker(symbol + suffix)
            fi     = ticker.fast_info
            price  = getattr(fi, "last_price", None)
            if price and float(price) > 0:
                return ticker, suffix
        except Exception:
            continue
    raise ValueError(
        f"No data found for '{symbol}' on NSE or BSE. "
        "Double-check the symbol (e.g. TCS, RELIANCE, HDFCBANK)."
    )


def fetch_quote(symbol: str) -> dict:
    """
    Fetch current quote using fast_info.
    ~2-5 min delay — much faster than .info.
    """
    symbol         = symbol.upper().strip()
    ticker, suffix = _get_ticker(symbol)
    fi             = ticker.fast_info

    price      = _safe_float(getattr(fi, "last_price",      None))
    prev_close = _safe_float(getattr(fi, "previous_close",  None))
    open_p     = _safe_float(getattr(fi, "open",            None))
    high       = _safe_float(getattr(fi, "day_high",        None))
    low        = _safe_float(getattr(fi, "day_low",         None))
    volume     = int(getattr(fi, "last_volume", 0) or 0)

    # Fill missing intraday fields from 1m history
    if not open_p or not high or not low:
        try:
            hist   = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                open_p = open_p or _safe_float(hist["Open"].iloc[0])
                high   = high   or _safe_float(hist["High"].max())
                low    = low    or _safe_float(hist["Low"].min())
                volume = volume or int(hist["Volume"].sum())
        except Exception:
            pass

    change     = round(price - prev_close, 2) if prev_close else 0
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

    market_time = getattr(fi, "market_time", None)
    date_str    = _format_date(
        market_time.timestamp() if hasattr(market_time, "timestamp") else market_time
    )

    return {
        "symbol":     symbol,
        "av_symbol":  symbol + suffix,
        "price":      price,
        "open":       open_p,
        "high":       high,
        "low":        low,
        "prev_close": prev_close,
        "volume":     volume,
        "change":     change,
        "change_pct": change_pct,
        "date":       date_str,
        "error":      None,
    }


def fetch_quotes(stocks: list) -> list:
    """Fetch quotes for a list of {symbol, name} dicts."""
    results = []
    for s in stocks:
        sym = s["symbol"].upper().strip()
        try:
            q         = fetch_quote(sym)
            q["name"] = s.get("name", sym)
            results.append(q)
            time.sleep(0.1)
        except Exception as e:
            results.append({
                "symbol": sym,
                "name":   s.get("name", sym),
                "error":  str(e),
            })
    return results


def fetch_chart_data(symbol: str, period: str = "30") -> list:
    """
    Fetch OHLCV history for charting.
    7 days  → 15m candles (intraday detail)
    30 days → daily candles
    60/90   → daily candles
    """
    symbol = symbol.upper().strip()
    chart  = []

    try:
        days = int(period)
    except (TypeError, ValueError):
        days = 30

    if days <= 7:
        yf_period   = "5d"
        yf_interval = "15m"
    elif days <= 30:
        yf_period   = "1mo"
        yf_interval = "1d"
    elif days <= 60:
        yf_period   = "2mo"
        yf_interval = "1d"
    else:
        yf_period   = "3mo"
        yf_interval = "1d"

    last_error = None

    for suffix in [".NS", ".BO"]:
        try:
            ticker = yf.Ticker(symbol + suffix)
            hist   = ticker.history(period=yf_period, interval=yf_interval)

            if hist.empty:
                continue

            if yf_interval == "1d":
                hist = hist.tail(days)

            for date, row in hist.iterrows():
                try:
                    date_str = (
                        date.strftime("%Y-%m-%d %H:%M")
                        if yf_interval != "1d"
                        else str(date.date())
                    )
                except Exception:
                    date_str = str(date)[:10]

                chart.append({
                    "date":   date_str,
                    "open":   round(float(row["Open"]),  2),
                    "high":   round(float(row["High"]),  2),
                    "low":    round(float(row["Low"]),   2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })

            if chart:
                break

        except Exception as e:
            last_error = e
            continue

    if not chart:
        raise ValueError(f"No chart data for '{symbol}': {last_error}")

    return chart


def fetch_intraday(symbol: str) -> list:
    """
    Fetch today's 1-minute candles for intraday view.
    Returns list of {date (HH:MM), open, high, low, close, volume}
    """
    symbol = symbol.upper().strip()

    for suffix in [".NS", ".BO"]:
        try:
            ticker  = yf.Ticker(symbol + suffix)
            hist    = ticker.history(period="1d", interval="1m")
            if hist.empty:
                continue
            candles = []
            for date, row in hist.iterrows():
                candles.append({
                    "date":   date.strftime("%H:%M"),
                    "open":   round(float(row["Open"]),  2),
                    "high":   round(float(row["High"]),  2),
                    "low":    round(float(row["Low"]),   2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            if candles:
                return candles
        except Exception:
            continue

    return []