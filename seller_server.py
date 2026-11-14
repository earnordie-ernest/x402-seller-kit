#!/usr/bin/env python3
"""
x402 Seller Kit — a minimal, working server that charges USDC per request.

Paid requests are verified and settled through the x402 facilitator, so you do NOT
need gas: the buyer signs an EIP-3009 authorization and the facilitator submits it.

Setup:
    pip install "x402[fastapi]" "x402[evm]" uvicorn
Run:
    PAY_TO=0xYourEVMAddress NETWORK=eip155:8453 PRICE='$0.001' \
        uvicorn seller_server:app --host 0.0.0.0 --port 8000
Test (no money moves until a real buyer pays):
    curl -i http://localhost:8000/price/ETH      # -> 402 + payment requirements
Networks: eip155:8453 = Base mainnet (USDC), eip155:84532 = Base Sepolia (testnet).
"""
import os

from fastapi import FastAPI

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

PAY_TO = os.environ.get("PAY_TO", "0x0000000000000000000000000000000000000000")
NETWORK = os.environ.get("NETWORK", "eip155:8453")
PRICE = os.environ.get("PRICE", "$0.001")
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://x402.org/facilitator")

app = FastAPI(title="x402 Seller Kit")

# 1. Facilitator verifies & settles payments for you (no gas on your side).
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))

# 2. Resource server knows which schemes/networks you accept.
server = x402ResourceServer(facilitator)
server.register(NETWORK, ExactEvmServerScheme())

# 3. Declare which routes are paid, and the price.
#    Route key format is "METHOD /path" (or just "/path" to accept any method).
routes = {
    "GET /price/ETH": RouteConfig(
        accepts=[PaymentOption(scheme="exact", price=PRICE, network=NETWORK, pay_to=PAY_TO)],
        description="ETH/USD spot price",
        mime_type="application/json",
    ),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


@app.get("/health")
async def health():
    # Free route: no entry in `routes`, so monitors can always reach it.
    return {"ok": True}


@app.get("/price/ETH")
async def price_eth():
    # Reached only once the request is paid. Replace with your real work.
    import json
    import urllib.request
    try:
        data = json.load(urllib.request.urlopen(
            "https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=10))
        return {"symbol": "ETH", "usd": float(data["data"]["amount"])}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
