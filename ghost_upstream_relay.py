#!/usr/bin/env python3
"""
Ghost Router - Multi-Upstream Sovereign Cloud Relay v8.0 (Port 8382)
Supports:
  1. Native Google AI Studio REST API (generativelanguage.googleapis.com via X-goog-api-key)
  2. OpenRouter / Public Unauthenticated Gateways (OpenAI-compatible format)
  3. Per-request UUID rotation, ephemeral node fingerprinting, and Connection: close teardown.
"""
import os
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

RELAY_HOST = "127.0.0.1"
RELAY_PORT = 8382

GOOGLE_AI_STUDIO_KEY = os.environ.get(
    "GOOGLE_AI_STUDIO_KEY",
    "AQ.Ab8RN6I1WietEnnh45VtIz6WfPh_MQSvBvf2rHHsc-U-Qvat6w"
)

PUBLIC_GATEWAYS = [
    "https://api.llm7.io/v1/chat/completions",
    "https://inference.net/v1/chat/completions"
]

VINE_SYSTEM_PROMPT = (
    "You are writing an authentic, first-person Amazon Vine product review. "
    "STRICT RULES: "
    "1. Review body MUST be strictly between 500 and 600 characters in length. "
    "2. Never use hyphens or dashes anywhere in the text. "
    "3. Use numeric digits only for quantities, measurements, and days (e.g., 2, 14). "
    "4. Write in natural, grounded first-person prose based on actual workshop testing. "
    "5. Output valid JSON ONLY with keys: 'title' (under 50 chars) and 'body' (500 to 600 chars)."
)

GENERAL_SYSTEM_PROMPT = (
    "You are an expert technical collaborator and systems engineer. "
    "Answer the user's prompt directly, thoroughly, and accurately with zero artificial length limits."
)

def is_google_model(model_name):
    m = model_name.lower()
    return any(k in m for k in ["gemini", "flash", "argon", "gemma", "google/"])

def normalize_google_model(model_name):
    clean = model_name.strip()
    if clean.startswith("google/"):
        clean = clean.replace("google/", "")
    if clean in ("flash", "gemini-flash", "gemini-flash-latest"):
        return "gemini-flash-latest"
    if clean in ("pro", "gemini-pro", "gemini-pro-latest"):
        return "gemini-pro-latest"
    return clean

def dispatch_google_ai_studio(model_name, sys_msg, user_msg, uuid_str, node_id):
    g_model = normalize_google_model(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent"

    payload = {
        "systemInstruction": {
            "parts": [{"text": sys_msg}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_msg}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7
        }
    }

    req_body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GOOGLE_AI_STUDIO_KEY,
        "X-Ghost-Session-UUID": uuid_str,
        "X-Ghost-Node-ID": node_id,
        "Connection": "close"
    }

    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw_data = resp.read().decode("utf-8")
        parsed = json.loads(raw_data)
        candidates = parsed.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts).strip()
        else:
            content = str(parsed)
        usage_meta = parsed.get("usageMetadata", {})
        tokens = usage_meta.get("totalTokenCount", 150)
        return content, tokens, f"google-ai-studio/{g_model}"

def dispatch_compute(model_name, prompt, mode, notes="", framing="self", uuid_str="", node_id=""):
    clean_model = model_name.strip()
    if clean_model.startswith("ollama-cloud/"):
        clean_model = clean_model.replace("ollama-cloud/", "")

    if mode == "vine":
        sys_msg = VINE_SYSTEM_PROMPT + f" Perspective framing: {framing}."
        user_msg = f"Product: {prompt}\nTester Notes: {notes}"
    else:
        sys_msg = GENERAL_SYSTEM_PROMPT
        user_msg = prompt

    last_error = ""

    if is_google_model(clean_model) and GOOGLE_AI_STUDIO_KEY:
        try:
            content, tokens, provider_tag = dispatch_google_ai_studio(clean_model, sys_msg, user_msg, uuid_str, node_id)
            return format_output(content, tokens, mode, prompt, provider_tag)
        except Exception as e:
            last_error = f"Google AI Studio error: {e}"

    payload = {
        "model": clean_model,
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.7
    }
    req_body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Ghost-Session-UUID": uuid_str,
        "X-Ghost-Node-ID": node_id,
        "Connection": "close"
    }

    for gateway in PUBLIC_GATEWAYS:
        req = urllib.request.Request(gateway, data=req_body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_data = resp.read().decode("utf-8")
                parsed = json.loads(raw_data)
                if "choices" in parsed and len(parsed["choices"]) > 0:
                    content = parsed["choices"][0]["message"]["content"].strip()
                    usage = parsed.get("usage", {}).get("total_tokens", 150)
                elif "response" in parsed:
                    content = parsed["response"].strip()
                    usage = 150
                else:
                    content = str(parsed)
                    usage = 150
                return format_output(content, usage, mode, prompt, gateway)
        except Exception as e:
            last_error = str(e)
            continue

    if GOOGLE_AI_STUDIO_KEY and not is_google_model(clean_model):
        try:
            content, tokens, provider_tag = dispatch_google_ai_studio("gemini-flash-latest", sys_msg, user_msg, uuid_str, node_id)
            return format_output(content, tokens, mode, prompt, f"fallback->{provider_tag}")
        except Exception as e:
            last_error += f" | Google fallback error: {e}"

    return {
        "title": "Gateway Circuit Standby",
        "body": f"All upstream routes exhausted for '{clean_model}'. Last diagnostic: {last_error}",
        "tokens": 0,
        "upstream": "none"
    }

def format_output(content, usage, mode, prompt, upstream_tag):
    if mode == "vine":
        try:
            cleaned = content.strip("`").replace("json\n", "", 1).strip()
            p_json = json.loads(cleaned)
            return {
                "title": p_json.get("title", prompt[:45]),
                "body": p_json.get("body", content).replace("-", " "),
                "tokens": usage,
                "upstream": upstream_tag
            }
        except Exception:
            return {
                "title": prompt[:45],
                "body": content.replace("-", " "),
                "tokens": usage,
                "upstream": upstream_tag
            }
    return {"title": "N/A", "body": content, "tokens": usage, "upstream": upstream_tag}

class SovereignRelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8")
        uuid_str = self.headers.get("X-Ghost-UUID", "00000000-0000-0000-0000-000000000000")
        node_id = self.headers.get("X-Ghost-Node-ID", "Ghost-Node-Default")

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            data = {"prompt": raw_body, "mode": "general", "model": "gemini-flash-latest"}

        mode = data.get("mode", "general")
        model = data.get("model", "gemini-flash-latest")
        prompt = data.get("prompt", data.get("product", ""))
        notes = data.get("notes", "")
        framing = data.get("framing", "self")

        result = dispatch_compute(model, prompt, mode, notes, framing, uuid_str, node_id)

        resp_obj = {
            "status": "routed_production_sovereign",
            "mode": mode,
            "model": model,
            "upstream": result["upstream"],
            "title": result["title"],
            "body": result["body"],
            "telemetry": {
                "session_uuid": uuid_str,
                "ephemeral_node": node_id,
                "compute_location": "100_percent_cloud_sovereign",
                "tokens_utilized": result["tokens"]
            }
        }
        out_bytes = json.dumps(resp_obj).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out_bytes)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(out_bytes)
        self.close_connection = True

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"[Ghost Sovereign Relay v8.0] Active on http://{RELAY_HOST}:{RELAY_PORT}")
    HTTPServer((RELAY_HOST, RELAY_PORT), SovereignRelayHandler).serve_forever()
