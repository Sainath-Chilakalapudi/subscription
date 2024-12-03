from flask import Flask
import os
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is Running!"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run_server)
    server.daemon = True  # This ensures the thread will be killed when main program exits
    server.start()
