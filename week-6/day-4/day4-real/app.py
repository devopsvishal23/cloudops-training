from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    APP_ENV  : {os.environ.get('APP_ENV', 'not set')}
    DB_HOST  : {os.environ.get('DB_HOST', 'not set')}
    LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'not set')}
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)