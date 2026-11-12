# IronCore Labs / Ghost Router Architecture Specification (v8.0)

## Overview
The **IronCore Labs Ghost Router** stack is an advanced, sovereign cloud-compute gateway engineered for Fedora Asahi (ARM64). It decouples local persistent identity, memory queues, and stateful prompt conditioning from stateful cloud execution, routing 100% of model compute to bleeding-edge cloud endpoints while ensuring absolute cryptographic and network anonymity.

---

## Architecture Stack

### 1. The Local C Daemon Proxy (`ghost_routerd` on port `8381`)
* **Role:** Intercepts inbound socket connections locally on `127.0.0.1:8381`.
* **Anonymization:** Dynamically generates a brand-new cryptographically random UUID (`X-Ghost-UUID`) and ephemeral node fingerprint (`X-Ghost-Node-ID`) on every single transmission.
* **Socket Hygiene:** Enforces strict `Connection: close` socket teardowns so no persistent keep-alive state or telemetry leaks back to upstream entities.

### 2. The Multi-Upstream Sovereign Relay (`ghost_upstream_relay.py` on port `8382`)
* **Role:** Acts as an intelligent translation and routing proxy.
* **Native Integration:** Directly interfaces with Google AI Studio (`generativelanguage.googleapis.com`) using secure API keys (e.g., `X-goog-api-key`) for native Gemini/Flash/Argon models.
* **Fallback Circuit Breaking:** Dynamically routes non-Google bleeding-edge models across unauthenticated public community mirrors (`api.llm7.io`, `inference.net`, etc.) to prevent account token exhaustion.

---

## Security & Privacy Guarantees
* **Zero Local Model Weight Footprint:** 100% of heavy token generation runs in the cloud.
* **Per-Request Isolation:** Every message is treated by the cloud provider as arriving from an entirely unlinked machine and ephemeral session.
* **Strict Key Partitioning:** Administrative keys and inference keys are isolated; unauthenticated public tiers operate with zero billing impact.
---
