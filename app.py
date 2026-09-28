import html
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import Flask, g, jsonify, request

app = Flask(__name__)


def connect():
    conn = sqlite3.connect(os.environ.get("DB_PATH", "app.db"))
    conn.row_factory = sqlite3.Row
    return conn


def db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = connect()
    conn.execute(
        "create table if not exists users ("
        "id integer primary key, username text unique, password text)"
    )
    conn.execute(
        "create table if not exists messages ("
        "id integer primary key, user_id integer, text text)"
    )
    username = os.environ.get("SEED_USERNAME")
    password = os.environ.get("SEED_PASSWORD")
    if username and password:
        row = conn.execute(
            "select 1 from users where username = ?", (username,)
        ).fetchone()
        if row is None:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "insert into users (username, password) values (?, ?)",
                (username, hashed),
            )
    conn.commit()
    conn.close()


def auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        except (jwt.PyJWTError, KeyError):
            return jsonify(error="unauthorized"), 401
        g.user_id = int(payload["sub"])
        return fn(*args, **kwargs)

    return wrapper


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify(error="invalid credentials"), 401
    row = db().execute(
        "select id, password from users where username = ?", (username,)
    ).fetchone()
    valid = False
    if row is not None:
        try:
            valid = bcrypt.checkpw(password.encode(), row["password"].encode())
        except ValueError:
            valid = False
    if not valid:
        return jsonify(error="invalid credentials"), 401
    token = jwt.encode(
        {"sub": str(row["id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return jsonify(token=token)


@app.get("/api/data")
@auth
def data():
    rows = db().execute("select id, username from users").fetchall()
    return jsonify(
        users=[{"id": row["id"], "username": html.escape(row["username"])} for row in rows]
    )


@app.post("/api/messages")
@auth
def create_message():
    text = (request.get_json(silent=True) or {}).get("text")
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="text required"), 400
    cur = db().execute(
        "insert into messages (user_id, text) values (?, ?)", (g.user_id, text)
    )
    db().commit()
    return jsonify(id=cur.lastrowid, text=html.escape(text)), 201


init_db()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
