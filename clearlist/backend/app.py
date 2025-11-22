import os
import logging
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://clearlist:clearlist@db:5432/clearlist")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/app/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ------------------------------------------------------------
# Logging (STDOUT only, using CRITICAL instead of FATAL)
# ------------------------------------------------------------
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,   # overwrite Flask/Werkzeug handlers
)

logger = logging.getLogger("clearlist")

# ------------------------------------------------------------
# Database Helpers
# ------------------------------------------------------------
def db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    try:
        logger.info("Initializing database...")
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                file_name TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database ready.")
    except Exception as e:
        logger.fatal(f"FATAL: Could not initialize DB: {e}")
        raise


# ------------------------------------------------------------
# Flask App
# ------------------------------------------------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/api/health")
def health():
    logger.debug("Health endpoint hit.")
    return {"status": "ok"}


@app.route("/api/todos", methods=["GET"])
def list_todos():
    logger.debug("Fetching todos...")
    try:
        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM todos ORDER BY created_at DESC;")
        todos = cur.fetchall()
        cur.close()
        conn.close()

        for t in todos:
            if t["file_name"]:
                t["file_url"] = f"/uploads/{t['file_name']}"

        logger.info(f"Returned {len(todos)} todos.")
        return jsonify(todos)
    except Exception as e:
        logger.error(f"Error listing todos: {e}")
        return {"error": "Internal error"}, 500


@app.route("/api/todos", methods=["POST"])
def create_todo():
    title = request.form.get("title")
    description = request.form.get("description")
    file = request.files.get("file")

    if not title:
        logger.warning("Attempted todo creation without title.")
        return {"error": "Title required"}, 400

    file_name = None

    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        from uuid import uuid4
        file_name = f"{uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, file_name))
        logger.debug(f"Saved file: {file_name}")

    try:
        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "INSERT INTO todos (title, description, file_name) VALUES (%s, %s, %s) RETURNING *;",
            (title, description, file_name),
        )
        todo = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if todo["file_name"]:
            todo["file_url"] = f"/uploads/{todo['file_name']}"

        logger.info(f"Created todo {todo['id']}")
        return jsonify(todo), 201

    except Exception as e:
        logger.error(f"Error creating todo: {e}")
        return {"error": "Internal error"}, 500


@app.route("/uploads/<path:filename>")
def uploads(filename):
    logger.debug(f"Serving file: {filename}")
    return send_from_directory(UPLOAD_FOLDER, filename)


# Start
if __name__ == "__main__":
    init_db()
    logger.info("Starting backend on port 5000.")
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
