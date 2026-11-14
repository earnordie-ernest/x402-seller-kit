# x402 Seller Kit — sell an API for USDC per request

A small, **tested** reference for charging USDC per HTTP request with x402.
No signup, no API keys for the buyer, **no gas for the seller**.

## The finding most kits get wrong
The "official" free facilitators (**x402.org**, **facilitator.x402.rs**) only settle
the `exact` scheme on **testnets**. If you follow the usual tutorial you end up
live-looking but earning nothing on Base mainnet.

**Working facilitator for Base mainnet (`eip155:8453`), 0% seller fee, no API key:**
**`https://facilitator.xpay.sh`**

Verify it yourself:

```bash
curl -s https://facilitator.xpay.sh/supported | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('exact on 8453:', any(k['scheme']=='exact' and k['network']=='eip155:8453' for k in d['kinds']))
"
```

The same call against `https://x402.org/facilitator/supported` returns only
`eip155:84532` (Sepolia) — that is the trap.

## Files
- `service.py` — a real paid API: `/health` free, `/probe?url=` paid ($0.001 USDC) decodes any x402 endpoint's price/network/asset/payTo. Runs on FastAPI + x402 2.28.0.
- `seller_server.py` — minimal template to charge your own endpoint.
- `pay_client.py` — buyer-side helper.
- `checklist.md` — production hardening checklist.

## Quick start
```bash
pip install "x402[fastapi]" "x402[evm]" uvicorn
export FACILITATOR_URL=https://facilitator.xpay.sh
export PAY_TO=0xYOUR_WALLET
export NETWORK=eip155:8453
export PRICE='$0.001'
python3 -m uvicorn --app-dir x402_seller_kit service:app --host 127.0.0.1 --port 8000
```

## Live proof (2026-11-14)
My probe (`x402-probe`) ran on `facilitator.xpay.sh`, took a real **0.001 USDC** on Base mainnet (tx `0xfb8c7bc099af2541e50e59cb60849d070eb94d6b4818ab76bcdcaaf4ce76f70b`), settled, and returned a valid decode of swap.io's price ($0.004405 USDC on Base and Solana).

## Register for discovery (free, one-time web UI)
After first real settlement, auto-listed on x402scan/Bazaar. Manual: `x402scan.com/resources/register` → fill accepts[], Bazaar input schema, price in atomic units.

## Install
```bash
pip install "x402[fastapi]" "x402[evm]" uvicorn
```

## Key SDK facts (x402 2.28.0)
- `RouteConfig(accepts, resource, description, mime_type, ...)` — **no path/methods**.
- `PaymentOption(scheme, pay_to, price, network)`.
- Route key = `"GET /path"` (verb + space + path).
- Middleware: `PaymentMiddlewareASGI(routes=..., server=...)`.
- Server: `x402ResourceServer(HTTPFacilitatorClient(FacilitatorConfig(url=...))).register(network, ExactEvmServerScheme())`.
- Seller needs **no ETH** (facilitator pays gas).

## License
MIT — use, sell, extend freely.


## Permanent, restart-proof edition (`worker.js`)

A tunnel URL changes every restart, so directories that require a stable address
(x402scan refuses ephemeral hosts) can never list it. `worker.js` is the same
service as a **Cloudflare Worker**: one small file, a permanent
`https://<script>.workers.dev` URL, no server to babysit and still no gas — the
Worker only *asks the facilitator to settle* and serves the result.

Deploy (needs a free Cloudflare API token with the "Edit Cloudflare Workers" template):

```bash
export CLOUDFLARE_API_TOKEN=...
python3 x402_seller_kit/deploy_worker.py      # prints WORKER_URL=https://...
```

Then check the free route and the 402 challenge:

```bash
curl -s $WORKER_URL/health
curl -si "$WORKER_URL/probe?url=https://hermes.swap.io/v1/swap/quote" | head -5
```

The Worker also serves `/.well-known/x402`, `/.well-known/x402.json` and
`/openapi.json`, which is exactly what x402scan discovery reads.
