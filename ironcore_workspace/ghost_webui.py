#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import json

WEB_HOST = "127.0.0.1"
WEB_PORT = 8080
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = 8381

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<title>IronCore Labs - Ghost Studio</title>
<style>
  body { font-family: monospace; background: #111; color: #eee; padding: 2rem; max-width: 800px; margin: auto; }
  input, select, textarea, button { background: #222; color: #0f0; border: 1px solid #444; padding: 8px; width: 100%; margin: 6px 0; font-family: monospace; }
  button { cursor: pointer; font-weight: bold; background: #1b3b1b; }
  .box { border: 1px solid #333; padding: 1rem; margin-top: 1rem; background: #181818; }
</style>
</head>
<body>
<h2>[IronCore Labs // Ghost Studio WebUI]</h2>
<label>Mode:</label>
<select id="mode"><option value="vine">Vine Review (500-600 chars)</option><option value="general">General AI Companion</option></select>
<label>Target Model:</label>
<input id="model" value="ollama-cloud/gemini-4-argon" />
<label>Framing:</label>
<select id="framing"><option value="self">Self</option><option value="wife">Wife</option><option value="daughter">Daughter</option></select>
<label>Product / Prompt:</label>
<textarea id="prompt" rows="3" placeholder="Enter product name or prompt..."></textarea>
<button onclick="sendReq()">DISPATCH ANONYMOUS REQUEST</button>
<div class="box" id="output">Ready.</div>
<script>
async function sendReq() {
  document.getElementById('output').innerText = 'Routing via 127.0.0.1:8381...';
  const res = await fetch('/dispatch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      mode: document.getElementById('mode').value,
      model: document.getElementById('model').value,
      framing: document.getElementById('framing').value,
      prompt: document.getElementById('prompt').value,
      product: document.getElementById('prompt').value
    })
  });
  const data = await res.json();
  const bodyText = data.body || '';
  document.getElementById('output').innerText =
    `Instance ID: ${data.telemetry?.ephemeral_instance_id || 'N/A'}\n` +
    `Char Count: ${bodyText.length}\n` +
    `Title: ${data.title || 'N/A'}\n\n` + bodyText;
}
</script>
</body>
</html>
"""

class WebUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length).decode("utf-8")
        http_req = (
            "POST /api/v1/route HTTP/1.1\r\n"
            f"Host: {ROUTER_HOST}:{ROUTER_PORT}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Connection: close\r\n\r\n"
            f"{payload}"
        )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ROUTER_HOST, ROUTER_PORT))
        s.sendall(http_req.encode("utf-8"))
        raw = s.recv(16384).decode("utf-8")
        s.close()
        _, _, body = raw.partition("\r\n\r\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

if __name__ == "__main__":
    print(f"[Ghost WebUI] Running on http://{WEB_HOST}:{WEB_PORT}")
    HTTPServer((WEB_HOST, WEB_PORT), WebUIHandler).serve_forever()
