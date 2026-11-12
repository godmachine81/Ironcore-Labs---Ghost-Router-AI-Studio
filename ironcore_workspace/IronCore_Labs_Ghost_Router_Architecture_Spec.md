# IronCore Labs - Ghost Router & Personal AI Studio Architecture

## Overview
Sovereign, terminal-first, stateless routing pipeline designed for Fedora Asahi Linux (ARM64 Apple Silicon).

## Components
1. `ghost_router_proxy_clean.c` -> Compile natively on Asahi ARM64:
   `gcc -g -O2 -fPIE -Wl,-z,relro -Wl,-z,now -o ghost_router_proxy_bin ghost_router_proxy_clean.c`
2. `ghost_client.py` -> CLI client supporting `--mode general`, `--mode vine` (500-600 chars), `--batch`, `--target-model`, `--learning-mode`, and `--verbose`.
3. `ghost_ollama_bridge.py` -> Local Ollama/Anthropic API translation bridge on `127.0.0.1:11434`.
4. `ghost_webui.py` -> Local browser dashboard on `127.0.0.1:8080`.

## Quick Start (Fedora Asahi ARM64)
```bash
gcc -g -O2 -fPIE -Wl,-z,relro -Wl,-z,now -o ghost_router_proxy_bin ghost_router_proxy_clean.c
./ghost_router_proxy_bin &
python3 ghost_client.py "Wheel Hub Resurfacing Tool" --mode vine --verbose
```
