import http.server
import threading

PORT = 8080  # You can choose any available port

def start_server():
    server = http.server.HTTPServer(('0.0.0.0', PORT), http.server.SimpleHTTPRequestHandler)
    server.serve_forever()

def run_server():
    thread = threading.Thread(target=start_server)
    thread.daemon = True  # So that the server dies when the main thread dies
    thread.start()

if __name__ == "__main__":
    run_server()
