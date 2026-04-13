"""
app.py - Market Pulse
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

ROOT     = os.path.dirname(os.path.abspath(__file__))
BACKEND  = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
sys.path.insert(0, BACKEND)

print(f"[startup] ROOT     = {ROOT}")
print(f"[startup] FRONTEND = {FRONTEND}")
print(f"[startup] frontend exists = {os.path.exists(FRONTEND)}")
print(f"[startup] index.html exists = {os.path.exists(os.path.join(FRONTEND, 'index.html'))}")

from flask import Flask, jsonify, send_from_directory, request, redirect
from flask_cors import CORS
from flask_login import LoginManager, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

import stock_fetcher   as sf
import gemini_analysis as ga
import chatbot         as cb
import database        as db
from auth   import auth_bp, init_oauth
from models import User

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-this")

# ── Critical: proxy fix for Render HTTPS ─────────────────────────────────────
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

is_prod = bool(os.environ.get("DATABASE_URL"))
app.config.update(
    SESSION_COOKIE_SECURE    = is_prod,
    SESSION_COOKIE_HTTPONLY  = True,
    SESSION_COOKIE_SAMESITE  = "Lax",
    REMEMBER_COOKIE_SECURE   = is_prod,
    REMEMBER_COOKIE_HTTPONLY = True,
)

CORS(app, supports_credentials=True)

# ── Flask-Login ───────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    row = db.get_user_by_id(int(user_id))
    return User(row) if row else None

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Login required"}), 401
    return redirect("/login.html")

init_oauth(app)
app.register_blueprint(auth_bp)

with app.app_context():
    db.init_db()


# ══════════════════════════════════════════════════════════════════════════════
#  FRONTEND ROUTES
#  NOTE: / and /index.html have NO @login_required
#  Auth is checked by the frontend JS itself via /auth/me
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve dashboard — auth checked by frontend JS"""
    return send_from_directory(FRONTEND, "index.html")

@app.route("/login.html")
def serve_login():
    return send_from_directory(FRONTEND, "login.html")

@app.route("/profile.html")
def serve_profile():
    return send_from_directory(FRONTEND, "profile.html")

@app.route("/<path:filename>")
def static_files(filename):
    file_path = os.path.join(FRONTEND, filename)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND, filename)
    return jsonify({"error": f"Not found: {filename}"}), 404


# ══════════════════════════════════════════════════════════════════════════════
#  API — all routes still protected with @login_required
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/watchlist", methods=["GET"])
@login_required
def get_watchlist():
    return jsonify(db.get_watchlist(current_user.id))

@app.route("/api/watchlist", methods=["POST"])
@login_required
def add_stock():
    body   = request.get_json(silent=True) or {}
    symbol = body.get("symbol", "").upper().strip()
    name   = body.get("name", symbol).strip()
    if not symbol:
        return jsonify({"error": "symbol is required"}), 400
    existing = db.get_watchlist(current_user.id)
    if any(s["symbol"] == symbol for s in existing):
        return jsonify({"error": f"{symbol} already in watchlist"}), 409
    try:
        quote         = sf.fetch_quote(symbol)
        quote["name"] = name
        db.add_to_watchlist(current_user.id, symbol, name)
        return jsonify({"message": f"{symbol} added", "quote": quote}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/watchlist/<symbol>", methods=["DELETE"])
@login_required
def remove_stock(symbol):
    if not db.remove_from_watchlist(current_user.id, symbol.upper()):
        return jsonify({"error": f"{symbol} not found"}), 404
    return jsonify({"message": f"{symbol} removed"})

@app.route("/api/stocks")
@login_required
def get_stocks():
    stocks = db.get_watchlist(current_user.id)
    if not stocks:
        return jsonify([])
    return jsonify(sf.fetch_quotes(stocks))

@app.route("/api/stock/<symbol>/chart")
@login_required
def get_chart(symbol):
    period = request.args.get("period", "30")
    try:
        return jsonify({
            "symbol": symbol.upper(),
            "chart":  sf.fetch_chart_data(symbol.upper(), period)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/stock/<symbol>/analyze", methods=["POST"])
@login_required
def analyze(symbol):
    body  = request.get_json(silent=True) or {}
    stock = body.get("stock", {})
    chart = body.get("chart", [])
    if not stock:
        return jsonify({"error": "stock data required"}), 400
    try:
        return jsonify(ga.analyze_stock(stock, chart))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    body    = request.get_json(silent=True) or {}
    message = body.get("message", "").strip()
    history = body.get("history", [])
    if not message:
        return jsonify({"error": "message is required"}), 400
    try:
        return jsonify({"reply": cb.get_chat_response(message, history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/portfolio", methods=["GET"])
@login_required
def get_portfolio():
    return jsonify(db.get_portfolio(current_user.id))

@app.route("/api/portfolio", methods=["POST"])
@login_required
def add_portfolio():
    body      = request.get_json(silent=True) or {}
    symbol    = body.get("symbol", "").upper().strip()
    name      = body.get("name", symbol).strip()
    quantity  = body.get("quantity")
    buy_price = body.get("buy_price")
    if not symbol or quantity is None or buy_price is None:
        return jsonify({"error": "symbol, quantity and buy_price required"}), 400
    try:
        quantity  = float(quantity)
        buy_price = float(buy_price)
    except ValueError:
        return jsonify({"error": "quantity and buy_price must be numbers"}), 400
    if db.upsert_portfolio(current_user.id, symbol, name, quantity, buy_price):
        return jsonify({"message": f"{symbol} saved to portfolio"}), 201
    return jsonify({"error": "Failed to save"}), 500

@app.route("/api/portfolio/<symbol>", methods=["DELETE"])
@login_required
def remove_portfolio(symbol):
    if not db.remove_from_portfolio(current_user.id, symbol.upper()):
        return jsonify({"error": f"{symbol} not found"}), 404
    return jsonify({"message": f"{symbol} removed"})


# ══════════════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=not is_prod)
# ── Run ───────────────────────────────────────────────────────────────────────
'''if __name__ == "__main__":
    import os

    is_prod = bool(os.environ.get("DATABASE_URL"))

    print("\n" + "=" * 52)
    print("  Market Pulse")
    print(f"  Mode : {'Production (PostgreSQL)' if is_prod else 'Local (SQLite)'}")
    print(f"  URL  : http://localhost:5000")
    print("=" * 52 + "\n")

    #port = int(os.environ.get("PORT", 5000))
    #app.run(host="0.0.0.0", port=port, debug=not is_prod)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
'''