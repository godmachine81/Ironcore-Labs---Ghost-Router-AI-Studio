#!/usr/bin/env python3
import subprocess
import time
import urllib.request
import json
import sys
import os

workspace_dir = os.path.abspath(os.path.dirname(__file__))

print("[Test] Compiling ghost_router_proxy_clean.c...")
comp = subprocess.run(["gcc", "-D_GNU_SOURCE", "-g", "-O2", "-o", "ghost_router_bin", "ghost_router_proxy_clean.c"], cwd=workspace_dir)
if comp.returncode != 0:
    print("Compilation failed!")
    sys.exit(1)
print("[Test] Compilation successful.")

print("[Test] Starting upstream relay (port 8382)...] ")
relay_proc = subprocess.Popen(["python3", "ghost_upstream_relay.py"], cwd=workspace_dir)
time.sleep(1)

print("[Test] Starting C proxy daemon (port 8381)...")
proxy_proc = subprocess.Popen(["./ghost_router_bin"], cwd=workspace_dir)
time.sleep(1)

print("[Test] Sending test payload through local proxy (port 8381)...")
try:
    req_data = json.dumps({
        "model": "anthropic/claude-opus-5.5",
        "prompt": "Test antenna feedline common-mode choke",
        "mode": "general"
    }).encode("utf-8")

    req = urllib.request.Request("http://127.0.0.1:8381/", data=req_data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body)
        print("[Test] SUCCESS! Received response from sovereign proxy stack:")
        print(json.dumps(parsed, indent=2))
except Exception as e:
    print(f"[Test] Integration test encountered exception: {e}")
finally:
    proxy_proc.terminate()
    relay_proc.terminate()
    print("[Test] Test harness shut down cleanly.")
