import http.server
import threading
from utils.config import Config

def start_server():
    server = http.server.HTTPServer(('0.0.0.0', Config.PORT), http.server.SimpleHTTPRequestHandler)
    server.serve_forever()

def run_server():
    thread = threading.Thread(target=start_server)
    thread.daemon = True  # So that the server dies when the main thread dies
    thread.start()

if __name__ == "__main__":
    run_server()
