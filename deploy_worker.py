#!/usr/bin/env python3
"""Deploy x402-probe (worker.js) to Cloudflare Workers and get a permanent URL.

Needs CLOUDFLARE_API_TOKEN in the environment (template: Edit Cloudflare Workers).
Account id is read automatically; pass it as argv[1] if the token sees several.

    python3 deploy_worker.py [ACCOUNT_ID]

Prints WORKER_URL=... on success.
"""
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.cloudflare.com/client/v4"
SCRIPT = "x402-probe"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()


def call(method, path, data=None, ctype="application/json"):
    url = API + path
    body = None
    headers = {"Authorization": "Bearer " + TOKEN}
    if data is not None:
        if ctype == "application/json":
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = data
            headers["Content-Type"] = ctype
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:1500]
    try:
        return 200, json.loads(txt)
    except Exception:
        return 200, txt[:1500]


def memberships():
    st, b = call("GET", "/memberships")
    ids = []
    if isinstance(b, dict):
        for m in b.get("result") or []:
            acc = m.get("account") or {}
            ids.append(acc.get("id"))
    return [i for i in ids if i]


def main():
    if not TOKEN:
        print("NO TOKEN: set CLOUDFLARE_API_TOKEN")
        return 1
    acct = sys.argv[1] if len(sys.argv) > 1 else None
    if not acct:
        ids = memberships()
        if not ids:
            st, b = call("GET", "/accounts")
            print("cannot list accounts", st, b)
            return 1
        acct = ids[0]
    print("account", acct)

    js = open(os.path.join(HERE, "worker.js"), "rb").read()
    meta = json.dumps({"main_module": "worker.js", "compatibility_date": "2025-04-01"})
    boundary = "----ernestworker"
    parts = []
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="metadata"')
    parts.append(b"Content-Type: application/json")
    parts.append(b"")
    parts.append(meta.encode())
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="worker.js"; filename="worker.js"')
    parts.append(b"Content-Type: application/javascript+module")
    parts.append(b"")
    parts.append(js)
    parts.append(("--" + boundary + "--").encode())
    parts.append(b"")
    payload = b"\r\n".join(parts)
    st, b = call(
        "PUT",
        f"/accounts/{acct}/workers/scripts/{SCRIPT}",
        payload,
        ctype="multipart/form-data; boundary=" + boundary,
    )
    print("deploy", st, str(b)[:400])

    st2, b2 = call("POST", f"/accounts/{acct}/workers/scripts/{SCRIPT}/subdomain", {"enabled": True})
    print("subdomain", st2, str(b2)[:400])
    st3, b3 = call("GET", f"/accounts/{acct}/workers/subdomain")
    sub = ""
    if isinstance(b3, dict):
        sub = (b3.get("result") or {}).get("subdomain") or ""
    if sub:
        print("WORKER_URL=https://%s.%s.workers.dev" % (SCRIPT, sub))
    else:
        print("subdomain info:", st3, str(b3)[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
