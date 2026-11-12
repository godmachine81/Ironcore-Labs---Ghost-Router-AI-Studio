#!/usr/bin/env python3
import sys
import argparse
import socket
import json
import random

ROUTER_HOST = "127.0.0.1"
ROUTER_PORT = 8381

AUTO_MODEL = "ollama-cloud/gemini-4-argon"

MODEL_POOLS = {
    "GOOGLE": ["ollama-cloud/gemini-4-argon", "ollama-cloud/gemini-4-carbon"],
    "CLAUDE": ["ollama-cloud/claude-opus-5.5", "ollama-cloud/claude-sonnet-4.0"],
    "CHATGPT": ["ollama-cloud/gpt-6-astra", "ollama-cloud/gpt-4.5-turbo"],
    "TOP": ["ollama-cloud/gemini-4-argon", "ollama-cloud/claude-opus-5.5", "ollama-cloud/gpt-6-astra"]
}

def resolve_models(target_spec):
    spec = target_spec.upper()
    if spec == "AUTO":
        return [AUTO_MODEL]
    elif spec == "RANDOM":
        all_models = MODEL_POOLS["TOP"] + MODEL_POOLS["GOOGLE"] + MODEL_POOLS["CLAUDE"] + MODEL_POOLS["CHATGPT"]
        return [random.choice(all_models)]
    elif spec == "ALLTOP":
        return MODEL_POOLS["TOP"]
    elif spec == "ALLGOOGLE":
        return MODEL_POOLS["GOOGLE"]
    elif spec == "ALLCLAUDE":
        return MODEL_POOLS["CLAUDE"]
    elif spec == "ALLCHATGPT":
        return MODEL_POOLS["CHATGPT"]
    else:
        return [target_spec]

def dispatch_request(payload_dict, verbose=False):
    payload = json.dumps(payload_dict)
    http_req = (
        "POST /api/v1/route HTTP/1.1\r\n"
        f"Host: {ROUTER_HOST}:{ROUTER_PORT}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Connection: close\r\n\r\n"
        f"{payload}"
    )
    if verbose:
        print(f"\n>> DISPATCHING TCP HTTP/1.1 REQUEST TO {ROUTER_HOST}:{ROUTER_PORT}:")
        print(http_req)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ROUTER_HOST, ROUTER_PORT))
        s.sendall(http_req.encode("utf-8"))
        raw_resp = s.recv(16384).decode("utf-8")
        s.close()
        if verbose:
            print("\n<< RECEIVED HTTP RESPONSE FROM GHOST ROUTER:")
            print(raw_resp)
        _, _, body = raw_resp.partition("\r\n\r\n")
        return json.loads(body)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def parse_queue_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    items = []
    raw_blocks = content.split("\n\n")
    for block in raw_blocks:
        block = block.strip()
        if block:
            lines = block.split("\n")
            product_name = lines[0]
            notes = " ".join(lines[1:]) if len(lines) > 1 else "Standard evaluation."
            items.append({"product": product_name, "notes": notes})
    return items

def main():
    parser = argparse.ArgumentParser(description="IronCore Labs - Ghost Studio CLI Client")
    parser.add_argument("prompt_or_item", nargs="?", help="Product name or general prompt text")
    parser.add_argument("--mode", default="general", choices=["general", "vine"], help="Execution mode: 'general' or 'vine'")
    parser.add_argument("--batch", help="Path to text/JSON file containing queue items")
    parser.add_argument("--target-model", default="AUTO", help="Model specification: AUTO, RANDOM, ALLTOP, ALLGOOGLE, ALLCLAUDE, ALLCHATGPT, or specific model name")
    parser.add_argument("--num-returns", type=int, default=1, help="Number of return variations to generate per item")
    parser.add_argument("--learning-mode", action="store_true", help="Enable multi-model compounding")
    parser.add_argument("--framing", default="self", choices=["self", "wife", "daughter"], help="Review framing perspective")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output full raw HTTP request/response headers and payloads")

    args = parser.parse_args()
    models_to_use = resolve_models(args.target_model)

    print("[IronCore Studio] Initializing pipeline...")
    print(f" -> Mode: {args.mode.upper()}")
    print(f" -> Target Models: {models_to_use}")
    print(f" -> Returns per Item: {args.num_returns}")
    print(f" -> Learning Mode: {'ENABLED (Compounding)' if args.learning_mode else 'DISABLED'}")
    print("-" * 60)

    queue = []
    if args.batch:
        queue = parse_queue_file(args.batch)
        print(f"[*] Loaded {len(queue)} items from batch file: {args.batch}")
    elif args.prompt_or_item:
        queue = [{"product": args.prompt_or_item, "notes": "Direct query."}]
    else:
        print("[-] Error: No input provided. Supply a prompt argument or use --batch <file>.")
        sys.exit(1)

    for idx, item in enumerate(queue, 1):
        prompt_text = item.get('product')
        print(f"\n[Item {idx}/{len(queue)}] Input: {prompt_text}")
        accumulated_notes = item.get("notes", "")

        for return_idx in range(1, args.num_returns + 1):
            for model in models_to_use:
                payload = {
                    "mode": args.mode,
                    "model": model,
                    "prompt": prompt_text,
                    "product": prompt_text,
                    "notes": accumulated_notes,
                    "framing": args.framing,
                    "return_index": return_idx
                }

                res = dispatch_request(payload, verbose=args.verbose)
                generated_body = res.get("body", res.get("response", "Response generated."))
                
                print(f"  -> Model [{model}] (Return #{return_idx}):")
                if args.mode == "vine":
                    print(f"     Title: {res.get('title', 'N/A')}")
                print(f"     Output: {generated_body}")
                print(f"     Telemetry ID: {res.get('telemetry', {}).get('ephemeral_instance_id', 'unknown')}")

                if args.learning_mode:
                    accumulated_notes += f" [Insights from {model}: {generated_body[:200]}]"
                    print(f"     [Learning Mode] Compounded output into secondary model context.")

    print("\n[+] Execution completed successfully via Ghost Router.")

if __name__ == "__main__":
    main()
