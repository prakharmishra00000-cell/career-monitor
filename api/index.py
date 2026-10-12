import json
from http.server import BaseHTTPRequestHandler
import urllib.request

# Vercel Serverless Function entry point
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        # Read and serve the dashboard UI
        try:
            with open('live_dashboard.py', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract HTML_TEMPLATE
                start = content.find('HTML_TEMPLATE = """') + len('HTML_TEMPLATE = """')
                end = content.find('"""', start)
                html = content[start:end]
                self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            self.wfile.write(f"<h1>Error loading dashboard: {e}</h1>".encode('utf-8'))
