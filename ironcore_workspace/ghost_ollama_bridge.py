#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import json

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 11434
ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = 8381

MODEL_ALIASES = {
    "argon4": "ollama-cloud/gemini-4-argon",
    "gemini-4-argon": "ollama-cloud/gemini-4-argon",
    "gemini-4-carbon": "ollama-cloud/gemini-4-carbon",
    "claude-opus-5.5": "ollama-cloud/claude-opus-5.5",
    "gpt-6-astra": "ollama-cloud/gpt-6-astra"
}

def forward_to_ghost_router(prompt, model):
    resolved_model = MODEL_ALIASES.get(model, model)
    payload = json.dumps({
        "mode": "general",
        "model": resolved_model,
        "prompt": prompt,
        "product": prompt,
        "notes": "Ollama Bridge Query",
        "framing": "self",
        "return_index": 1
    })
    http_req = (
        "POST /api/v1/route HTTP/1.1\r\n"
        f"Host: {ROUTER_HOST}:{ROUTER_PORT}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Connection: close\r\n\r\n"
        f"{payload}"
    )
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10.0)
    s.connect((ROUTER_HOST, ROUTER_PORT))
    s.sendall(http_req.encode("utf-8"))
    raw_resp = s.recv(16384).decode("utf-8")
    s.close()
    _, _, body = raw_resp.partition("\r\n\r\n")
    return json.loads(body)

class OllamaBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/tags":
            models = [{"name": k, "model": k} for k in MODEL_ALIASES.keys()]
            resp = json.dumps({"models": models}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Ollama is running (Ghost Router Bridge)")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
        model = post_data.get("model", "gemini-4-argon")
        
        if self.path == "/api/generate":
            prompt = post_data.get("prompt", "")
            routed = forward_to_ghost_router(prompt, model)
            out = json.dumps({
                "model": model,
                "response": routed.get("body", ""),
                "done": True
            }).encode("utf-8")
        elif self.path == "/api/chat":
            messages = post_data.get("messages", [])
            prompt = messages[-1].get("content", "") if messages else ""
            routed = forward_to_ghost_router(prompt, model)
            out = json.dumps({
                "model": model,
                "message": {"role": "assistant", "content": routed.get("body", "")},
                "done": True
            }).encode("utf-8")
        else:
            prompt = str(post_data)
            routed = forward_to_ghost_router(prompt, model)
            out = json.dumps({"content": [{"type": "text", "text": routed.get("body", "")}]}).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

if __name__ == "__main__":
    server = HTTPServer((BRIDGE_HOST, BRIDGE_PORT), OllamaBridgeHandler)
    print(f"[Ghost Ollama Bridge] Listening on http://{BRIDGE_HOST}:{BRIDGE_PORT} -> Routing via {ROUTER_HOST}:{ROUTER_PORT}")
    server.serve_forever()
