from flask import Flask, jsonify
import os
import psycopg2

app = Flask(__name__)

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

@app.route("/health")
def health()
    try:
        conn = get_db()
        conn.close()
        db_status = "ok"
    except Exception as e:
        db_status = str(e)
    return jsonify({"status": "ok", "db": db_status, "env": os.getenv("APP_ENV", "local")})

@app.route("/")
def index():
    return jsonify({"message": "cloudops upskill — week 4"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)