"""
database.py - SQLite locally, PostgreSQL on Render
Handles users (Google + email/password), watchlist, portfolio
"""

import os
import sqlite3
import hashlib
import secrets

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    conn = sqlite3.connect("market.db")
    conn.row_factory = sqlite3.Row
    return conn

def p():
    return "%s" if USE_POSTGRES else "?"

def init_db():
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                google_id     TEXT UNIQUE,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                picture       TEXT,
                password_hash TEXT,
                auth_type     TEXT DEFAULT 'google',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id       SERIAL PRIMARY KEY,
                user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol   TEXT NOT NULL,
                name     TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol)
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id        SERIAL PRIMARY KEY,
                user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol    TEXT NOT NULL,
                name      TEXT NOT NULL,
                quantity  REAL NOT NULL,
                buy_price REAL NOT NULL,
                bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol)
            )""")
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id     TEXT UNIQUE,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                picture       TEXT,
                password_hash TEXT,
                auth_type     TEXT DEFAULT 'google',
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                symbol   TEXT NOT NULL,
                name     TEXT NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                symbol    TEXT NOT NULL,
                name      TEXT NOT NULL,
                quantity  REAL NOT NULL,
                buy_price REAL NOT NULL,
                bought_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
    conn.commit()
    cur.close()
    conn.close()
    print("  DB ready")

def row_to_dict(cur, row):
    if USE_POSTGRES:
        return dict(zip([d[0] for d in cur.description], row))
    return dict(row)

# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h    = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

# ── User ops ──────────────────────────────────────────────────────────────────
def upsert_user(google_id, email, name, picture) -> dict:
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO users (google_id, email, name, picture, auth_type)
            VALUES (%s,%s,%s,%s,'google')
            ON CONFLICT (google_id) DO UPDATE
                SET name=EXCLUDED.name, picture=EXCLUDED.picture
            RETURNING *""", (google_id, email, name, picture))
        row  = cur.fetchone()
        user = row_to_dict(cur, row)
    else:
        cur.execute(f"""
            INSERT INTO users (google_id, email, name, picture, auth_type)
            VALUES (?,?,?,?,'google')
            ON CONFLICT(google_id) DO UPDATE
                SET name=excluded.name, picture=excluded.picture
        """, (google_id, email, name, picture))
        cur.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
        user = row_to_dict(cur, cur.fetchone())
    conn.commit(); cur.close(); conn.close()
    return user

def register_user(email, name, password) -> dict | None:
    """Register with email/password. Returns user or None if email exists."""
    conn = get_conn()
    cur  = conn.cursor()
    try:
        ph = hash_password(password)
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO users (email, name, password_hash, auth_type)
                VALUES (%s,%s,%s,'email') RETURNING *
            """, (email, name, ph))
            row  = cur.fetchone()
            user = row_to_dict(cur, row)
        else:
            cur.execute("""
                INSERT INTO users (email, name, password_hash, auth_type)
                VALUES (?,?,?,'email')
            """, (email, name, ph))
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = row_to_dict(cur, cur.fetchone())
        conn.commit()
        return user
    except Exception:
        conn.rollback()
        return None
    finally:
        cur.close(); conn.close()

def login_email_user(email, password) -> dict | None:
    """Verify email/password. Returns user or None."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE email = {p()}", (email,))
    row  = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return None
    user = dict(row) if not USE_POSTGRES else row_to_dict(cur, row)
    if not user.get("password_hash"):
        return None
    if verify_password(password, user["password_hash"]):
        return user
    return None

def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {p()}", (user_id,))
    row  = cur.fetchone()
    cur.close(); conn.close()
    if not row: return None
    return dict(row) if not USE_POSTGRES else row_to_dict(cur, row)

# ── Watchlist ─────────────────────────────────────────────────────────────────
def get_watchlist(user_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"SELECT symbol, name FROM watchlist WHERE user_id={p()} ORDER BY added_at", (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) if not USE_POSTGRES else {"symbol":r[0],"name":r[1]} for r in rows]

def add_to_watchlist(user_id, symbol, name):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO watchlist (user_id,symbol,name) VALUES ({p()},{p()},{p()})", (user_id, symbol.upper(), name))
        conn.commit(); return True
    except: conn.rollback(); return False
    finally: cur.close(); conn.close()

def remove_from_watchlist(user_id, symbol):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"DELETE FROM watchlist WHERE user_id={p()} AND symbol={p()}", (user_id, symbol.upper()))
    affected = cur.rowcount; conn.commit(); cur.close(); conn.close()
    return affected > 0

# ── Portfolio ─────────────────────────────────────────────────────────────────
def get_portfolio(user_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"SELECT symbol,name,quantity,buy_price,bought_at FROM portfolio WHERE user_id={p()} ORDER BY bought_at", (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    cols = ["symbol","name","quantity","buy_price","bought_at"]
    return [dict(zip(cols, r)) if USE_POSTGRES else dict(r) for r in rows]

def upsert_portfolio(user_id, symbol, name, quantity, buy_price):
    conn = get_conn(); cur = conn.cursor()
    try:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO portfolio (user_id,symbol,name,quantity,buy_price)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(user_id,symbol) DO UPDATE
                    SET quantity=EXCLUDED.quantity, buy_price=EXCLUDED.buy_price
            """, (user_id, symbol.upper(), name, quantity, buy_price))
        else:
            cur.execute("""
                INSERT INTO portfolio (user_id,symbol,name,quantity,buy_price)
                VALUES (?,?,?,?,?)
                ON CONFLICT(user_id,symbol) DO UPDATE
                    SET quantity=excluded.quantity, buy_price=excluded.buy_price
            """, (user_id, symbol.upper(), name, quantity, buy_price))
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); print(f"Portfolio error: {e}"); return False
    finally:
        cur.close(); conn.close()

def remove_from_portfolio(user_id, symbol):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"DELETE FROM portfolio WHERE user_id={p()} AND symbol={p()}", (user_id, symbol.upper()))
    affected = cur.rowcount; conn.commit(); cur.close(); conn.close()
    return affected > 0