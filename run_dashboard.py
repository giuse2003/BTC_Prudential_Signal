import http.server
import socketserver
import webbrowser
import threading
import time
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PORT = 8000
HOST = "127.0.0.1"
Handler = http.server.SimpleHTTPRequestHandler

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
            print(f"Server della dashboard attivo all'indirizzo: http://{HOST}:{PORT}")
            print("Premi CTRL+C per arrestare il server.")
            httpd.serve_forever()
    except Exception as e:
        print(f"Errore nell'avvio del server: {e}")

if __name__ == "__main__":
    print("Avvio del server locale per la Dashboard (BTC Monitor)...")
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    
    # Aspetta che il server parta
    time.sleep(1)
    
    url = f"http://{HOST}:{PORT}/index.html"
    print(f"Apertura del browser su: {url}...")
    webbrowser.open(url)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDashboard server arrestato.")
