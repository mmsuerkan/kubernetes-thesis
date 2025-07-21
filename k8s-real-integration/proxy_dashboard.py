#!/usr/bin/env python3
"""
Simple HTTP server to serve dashboard and proxy Go service requests
This avoids CORS issues by serving everything from the same origin
"""
import http.server
import socketserver
import urllib.request
import urllib.parse
import json
from urllib.error import URLError

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Proxy Go service requests
        if self.path.startswith('/go/'):
            # Remove /go prefix and forward to Go service
            go_path = self.path[3:]  # Remove '/go'
            go_url = f"http://localhost:8080{go_path}"
            
            try:
                with urllib.request.urlopen(go_url) as response:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(response.read())
            except URLError as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = json.dumps({"error": str(e)}).encode()
                self.wfile.write(error_response)
            return
        
        # Serve static files normally
        super().do_GET()

def run_server(port=3000):
    handler = ProxyHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 Dashboard Proxy Server başlatıldı")
        print(f"📱 Dashboard URL: http://localhost:{port}/dashboard.html")
        print(f"🔄 Go Service Proxy: http://localhost:{port}/go/api/v1/health")
        print(f"💡 CTRL+C ile durdurun")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server durduruldu")

if __name__ == "__main__":
    run_server()