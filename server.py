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
    """Ping the server every 15 minutes to prevent sleeping"""
    while True:
        try:
            # Get the server URL from environment or use default
            server_url = os.environ.get('SERVER_URL', 'http://localhost:10000')
            # Make requests to different endpoints
            requests.get(f"{server_url}/")
            requests.get(f"{server_url}/health")
            requests.get(f"{server_url}/ping")
            print("Server pinged successfully!")
        except Exception as e:
            print(f"Failed to ping server: {str(e)}")
        # Sleep for 15 minutes
        time.sleep(900)  # 15 minutes = 900 seconds

def run_server():
    """Run the Flask server"""
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Start the server and ping mechanism in separate threads"""
    # Start the Flask server in a thread
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Start the ping mechanism in another thread
    ping_thread = Thread(target=ping_server)
    ping_thread.daemon = True
    ping_thread.start()

if __name__ == "__main__":
    keep_alive()
