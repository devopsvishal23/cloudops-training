from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "env": os.getenv("APP_ENV", "local")})

@app.route("/")
def index():
    return jsonify({"message": "Vishal-18-June-2026 cloudops upskill — week 4"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)