#!/usr/bin/env python3
"""
Buyer-side probe: hit a URL and show the 402 payment requirements (no money spent).
Usage: python3 pay_client.py http://localhost:8000/price/ETH
"""
import sys, json, urllib.request, urllib.error

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/price/ETH"
req = urllib.request.Request(url, headers={"Accept": "application/json"})
try:
    r = urllib.request.urlopen(req, timeout=15)
    print("200 OK — this resource is free or already paid:", r.read().decode()[:400])
except urllib.error.HTTPError as e:
    if e.code == 402:
        body = e.read().decode()
        print("402 Payment Required — here is what the seller asks for:")
        try:
            print(json.dumps(json.loads(body), indent=2)[:1200])
        except Exception:
            print(body[:600])
    else:
        print("HTTP", e.code, e.read().decode()[:300])
