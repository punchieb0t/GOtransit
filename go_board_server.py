#!/usr/bin/env python3
"""
GO Transit Board Server
Serves the departure board and proxies API requests to avoid CORS
"""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.parse
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY = "30026843"
API_BASE = "https://api.openmetrolinx.com/OpenDataAPI/api/V1"

class CORSProxyHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve from script directory
        return os.path.join(SCRIPT_DIR, path.lstrip('/'))
    def do_GET(self):
        # Proxy API requests
        if self.path.startswith('/api/'):
            # Parse the stop code from query string
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            stop = params.get('stop', ['CL'])[0]
            
            # Fetch from Metrolinx
            url = f"{API_BASE}/Stop/NextService?key={API_KEY}&stopCode={stop}&limit=10"
            try:
                resp = urllib.request.urlopen(url, timeout=30)
                data = resp.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            # Serve static files
            super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

PORT = 8080
print(f"🚂 GO Transit Board")
print(f"   http://localhost:{PORT}/go_board.html")
print(f"   Press Ctrl+C to stop")

server = HTTPServer(('0.0.0.0', PORT), CORSProxyHandler)
server.serve_forever()
