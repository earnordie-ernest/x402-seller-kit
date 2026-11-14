# x402 Seller Kit — sell an API for USDC per request

A small, **tested** reference for charging USDC per HTTP request with x402.
No signup, no API keys for the buyer, **no gas for the seller**.

## The finding most kits get wrong
The "official" free facilitators (**x402.org**, **facilitator.x402.rs**) only settle
the `exact` scheme on **testnets**. If you follow the usual tutorial you end up
live-looking but earning nothing on Base mainnet.

A facilitator that *does* support **Base mainnet (`eip155:8453`)** with `exact`,
at **0% seller fee**, is **https://x402.dexter.cash**.

Verify it yourself in one call:

    curl -s https://x402.dexter.cash/supported | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted({(k['scheme'],k['network']) for k in d['kinds'] if '8453' in str(k['network'])}))"

You should see `('exact', 'eip155:8453')` among the results. The same call against
`https://x402.org/facilitator/supported` returns only `eip155:84532` (Sepolia) —
that is the trap.

## Install
```bash
pip install "x402[fastapi]" "x402[evm]" uvicorn
```

## Run (Base mainnet, real money)
```bash
PAY_TO=0xYourEVMAddress \
NETWORK=eip155:8453 \
FACILITATOR_URL=https://x402.dexter.cash \
PRICE='$0.001' \
python3 seller_server.py
```

Set `NETWORK=eip155:84532` and drop `FACILITATOR_URL` to test free on Sepolia.

## Files
- `seller_server.py` — minimal paid endpoint (`/health` free, `/price/ETH` paid).
- `service.py` — a real product: **`/probe?url=...`** decodes any x402 endpoint's
  price/network/asset/payTo, handling both v2 base64-header and v1 JSON-body
  challenges. Refuses private/SSRF hosts. This is what makes it worth paying for.
- `pay_client.py` — how a buyer pays programmatically.

## Expose it publicly for free
```bash
./cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate
```
Cloudflare prints a `https://<name>.trycloudflare.com` URL that reaches your service.

## Gotchas learned the hard way
- Route keys are `"METHOD /path"`. A bare path matches any method.
- The paid route must be **registered in `routes`** or it answers 200 unpaid.
- x402 **v1** endpoints put the challenge in the **JSON body**, not a header —
  handle both or your client breaks on older sellers.
- Your wallet needs **no ETH** to *receive*: the facilitator pays the gas.
  It does need ETH only if *you* send an on-chain transfer yourself.

## Price the thing people actually can't do
Nobody pays for an ETH price feed (it's free everywhere). They pay for work that
is annoying, gated, or needs another payment — e.g. "what does this endpoint
charge, without paying it?" Charge $0.001 and be the cheapest way to find out.
