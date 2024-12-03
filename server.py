from flask import Flask
import os
import requests
from threading import Thread
import time

app = Flask(__name__)

# Dummy response for root endpoint
@app.route('/')
def home():
    return "Telegram Subscription Bot is Running! 🤖"

# Dummy response for health check
@app.route('/health')
def health():
    return {"status": "healthy", "message": "Bot is operational"}

# Dummy response for ping
@app.route('/ping')
def ping():
    return "pong"

def ping_server():
    while True:
        try:
            port = int(os.environ.get("PORT", 10000))
            server_url = os.environ.get('SERVER_URL', f'http://0.0.0.0:{port}')
            requests.get(f"{server_url}/")
            requests.get(f"{server_url}/health")
            requests.get(f"{server_url}/ping")
            print("Server pinged successfully!")
        except Exception as e:
            print(f"Failed to ping server: {str(e)}")
            # Maybe add some retry logic here
        time.sleep(900)

def run_server():
    """Run the Flask server"""
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Start the server and ping mechanism in separate threads"""
    try:
        # Start the Flask server in a thread
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Give the server a moment to start up
        time.sleep(5)  # Wait 5 seconds before starting ping

        # Start the ping mechanism in another thread
        ping_thread = Thread(target=ping_server)
        ping_thread.daemon = True
        ping_thread.start()
    except Exception as e:
        print(f"Error in keep_alive: {str(e)}")

if __name__ == "__main__":
    keep_alive()
