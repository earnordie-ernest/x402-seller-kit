#!/usr/bin/env python3
"""
x402 Probe — a paid API that tells you what an x402 endpoint charges.

Problem it solves: an agent that finds a URL advertising "pay per call" cannot
learn the price, the network, the asset or the payTo address without paying
first. This service sends one unpaid request and returns the 402 challenge,
decoded. Price: $0.001 USDC per call on Base mainnet (eip155:8453).

Free:  GET /health
Paid:  GET /probe?url=<endpoint>
Paid:  GET /price/ETH

Runs behind a tunnel. Seller-side settlement goes through the facilitator,
so no gas is needed on the seller side.
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from fastapi import FastAPI, Query, Request

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

PAY_TO = os.environ.get("PAY_TO", "0xEe523a5145cfaEa8cCEc34Fb364a2A92Fad62A3a")
NETWORK = os.environ.get("NETWORK", "eip155:8453")
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://facilitator.xpay.sh")
PRICE = os.environ.get("PRICE", "$0.001")

app = FastAPI(title="x402 Probe")

facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
server = x402ResourceServer(facilitator)
server.register(NETWORK, ExactEvmServerScheme())

routes = {
    "GET /probe": RouteConfig(
        accepts=[PaymentOption(scheme="exact", price=PRICE, network=NETWORK, pay_to=PAY_TO)],
        description="Decode any x402 endpoint's price, network, asset and payTo",
        mime_type="application/json",
    ),
    "GET /price/ETH": RouteConfig(
        accepts=[PaymentOption(scheme="exact", price=PRICE, network=NETWORK, pay_to=PAY_TO)],
        description="ETH/USD spot price",
        mime_type="application/json",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


def decode_challenge(value):
    """Decode the base64 payment-required header into readable terms."""
    out = {"raw_header_present": bool(value)}
    try:
        padded = value + "=" * (-len(value) % 4)
        doc = json.loads(base64.b64decode(padded))
    except Exception as e:
        out["decode_error"] = str(e)[:200]
        return out
    out["x402Version"] = doc.get("x402Version")
    res = doc.get("resource") or {}
    out["resource"] = {"url": res.get("url"), "description": res.get("description")}
    accepts = []
    for a in doc.get("accepts") or []:
        amt = a.get("amount")
        try:
            usd = float(amt) / 1_000_000 if amt else None
        except Exception:
            usd = None
        accepts.append({
            "scheme": a.get("scheme"),
            "network": a.get("network"),
            "asset": a.get("asset"),
            "amount_atomic": amt,
            "amount_usd": usd,
            "payTo": a.get("payTo") or a.get("pay_to"),
            "maxTimeoutSeconds": a.get("maxTimeoutSeconds"),
        })
    out["accepts"] = accepts
    return out


@app.get("/health")
async def health():
    return {"ok": True, "service": "x402-probe", "network": NETWORK, "price": PRICE}


@app.get("/.well-known/x402")
async def wellknown(request: Request):
    import os as _os
    base = str(request.base_url).rstrip("/")
    return {
        "version": 1,
        "resources": [base + "/probe?url=https://hermes.swap.io/v1/swap/quote"],
        "ownershipProofs": [PAY_TO],
        "instructions": "GET /probe?url=<paid-endpoint> returns that endpoint's x402 challenge (price/network/asset/payTo).",
    }

@app.get("/openapi.json")
async def openapi(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "openapi": "3.1.0",
        "info": {"title": "x402 Probe", "version": "1.0.0"},
        "paths": {
            "/probe": {
                "get": {
                    "operationId": "probeEndpoint",
                    "summary": "Decode any x402 endpoint's price and payTo without paying it.",
                    "parameters": [{"name": "url", "in": "query", "required": True,
                                    "schema": {"type": "string", "format": "uri"}}],
                    "x-payment-info": {"protocols": ["x402"],
                                       "price": {"mode": "fixed", "currency": "USD", "amount": "0.001"}},
                    "responses": {
                        "200": {"description": "Decoded challenge"},
                        "402": {"description": "Payment required"},
                    },
                }
            }
        },
        "x-discovery": {"ownershipProofs": [PAY_TO]},
    }

@app.get("/.well-known/x402.json")
async def manifest(request: Request):
    import os as _os
    base = str(request.base_url).rstrip("/")
    return {
        "x402Version": 2,
        "name": "x402-probe",
        "description": "Decode any x402 endpoint's price, network, asset and payTo without paying it.",
        "resources": [{
            "resource": base + "/probe",
            "method": "GET",
            "description": "Pass ?url=<paid endpoint>; returns its x402 challenge (price/network/asset/payTo). Handles v2 header and v1 JSON-body challenges.",
            "price": _os.environ.get("PRICE", "$0.001"),
            "network": NETWORK,
            "payTo": PAY_TO,
        }],
    }

@app.get("/probe")
async def probe(url: str = Query(..., description="x402 endpoint URL to inspect")):
    """Fetch the endpoint without paying and decode its 402 requirements."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return {"error": "url must be an absolute http(s) URL"}
    # Refuse to be used as an SSRF proxy against local/private addresses.
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.startswith(
            ("10.", "192.168.", "169.254.", "172.16.", "172.17.", "172.18.",
             "172.19.", "172.2", "172.30.", "172.31.")):
        return {"error": "private/internal addresses are not allowed"}

    def fetch(method):
        req = urllib.request.Request(url, headers={"User-Agent": "x402-probe/1.0"},
                                     method=method,
                                     data=b"{}" if method == "POST" else None)
        return urllib.request.urlopen(req, timeout=15)

    result = {"requested_url": url, "method_used": "GET"}
    try:
        try:
            r = fetch("GET")
        except urllib.error.HTTPError as e0:
            if e0.code not in (405, 400, 415, 404):
                raise
            result["method_used"] = "POST"
            r = fetch("POST")
        result["status"] = r.status
        result["paid"] = False
        result["note"] = "endpoint answered without payment; no x402 challenge present"
        body = r.read(2048).decode("utf-8", "replace")
        result["body_preview"] = body[:600]
        return result
    except urllib.error.HTTPError as e:
        result["status"] = e.code
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        hdr = hdrs.get("payment-required") or hdrs.get("x-payment-required")
        body_txt = ""
        try:
            body_txt = e.read(4096).decode("utf-8", "replace")
        except Exception:
            pass
        if e.code == 402 and hdr:
            result["paid"] = True
            result["challenge"] = decode_challenge(hdr)
        elif e.code == 402 and body_txt.strip().startswith("{"):
            # x402 v1 style: the challenge is the JSON response body itself.
            try:
                doc = json.loads(body_txt)
            except Exception:
                doc = {}
            accepts = []
            for a in doc.get("accepts") or []:
                amt = a.get("maxAmountRequired") or a.get("amount")
                try:
                    usd = float(amt) / 1_000_000 if amt else None
                except Exception:
                    usd = None
                accepts.append({
                    "scheme": a.get("scheme"), "network": a.get("network"),
                    "asset": a.get("asset"), "amount_atomic": amt, "amount_usd": usd,
                    "payTo": a.get("payTo"), "maxTimeoutSeconds": a.get("maxTimeoutSeconds"),
                })
            result["paid"] = True
            result["challenge"] = {
                "source": "json_body", "x402Version": doc.get("x402Version"),
                "resource": {"url": (doc.get("resource") or {}).get("url") or url,
                             "description": (doc.get("resource") or {}).get("description") or doc.get("description")},
                "accepts": accepts,
            }
        else:
            result["paid"] = False
            result["headers_seen"] = [k for k in hdrs if "payment" in k or k.startswith("x-")]
            try:
                result["body_preview"] = e.read(1024).decode("utf-8", "replace")[:600]
            except Exception:
                pass
        return result
    except Exception as e:
        return {"requested_url": url, "error": type(e).__name__, "detail": str(e)[:200]}


@app.get("/price/ETH")
async def price_eth():
    try:
        data = json.load(urllib.request.urlopen(
            "https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=10))
        return {"symbol": "ETH", "usd": float(data["data"]["amount"]), "source": "coinbase"}
    except Exception as e:
        return {"error": str(e)[:200]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
