/**
 * x402-probe — Cloudflare Worker edition (permanent URL, no server, no gas).
 *
 * Free endpoints:
 *   GET /health
 *   GET /.well-known/x402        (v1 discovery)
 *   GET /.well-known/x402.json   (v2 manifest, Bazaar-ish)
 *   GET /openapi.json            (what x402scan reads first)
 * Paid endpoints (x402 `exact`, USDC on Base, settle via facilitator.xpay.sh):
 *   GET /probe?url=<endpoint>    decode any endpoint's x402 price/network/payTo without paying it
 *   GET /price/ETH               ETH/USD spot price
 *
 * The seller needs no ETH: the facilitator broadcasts the settlement.
 */

const PAY_TO = "0xEe523a5145cfaEa8cCEc34Fb364a2A92Fad62A3a";
const NETWORK = "eip155:8453";
const FACILITATOR = "https://facilitator.xpay.sh";
const PRICE = "$0.001";
const ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // USDC on Base
const AMOUNT_ATOMIC = "1000"; // 0.001 USDC
const MAX_TIMEOUT = 300;

const PAID = {
  "/probe": "Decode any x402 endpoint's price, network, asset and payTo",
  "/price/ETH": "ETH/USD spot price",
};

function b64encode(obj) {
  const s = JSON.stringify(obj);
  const bytes = new TextEncoder().encode(s);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
function b64decode(str) {
  const bin = atob(str.replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes));
}

function challenge(url, description) {
  return {
    x402Version: 2,
    resource: { url, description, mimeType: "application/json" },
    accepts: [
      {
        scheme: "exact",
        network: NETWORK,
        asset: ASSET,
        amount: AMOUNT_ATOMIC,
        payTo: PAY_TO,
        maxTimeoutSeconds: MAX_TIMEOUT,
        extra: { name: "USD Coin", version: "2" },
      },
    ],
  };
}

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-expose-headers": "PAYMENT-REQUIRED,PAYMENT-RESPONSE",
};

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body, null, 1), {
    status,
    headers: { "content-type": "application/json", ...CORS, ...extra },
  });
}

function paymentRequired(ch) {
  return json(ch, 402, {
    "payment-required": b64encode(ch),
    "x-payment-required": b64encode(ch),
  });
}

async function decodeChallenge(value) {
  const out = { raw_header_present: !!value };
  try {
    const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
    const doc = b64decode(padded);
    out.x402Version = doc.x402Version;
    const res = doc.resource || {};
    out.resource = { url: res.url, description: res.description };
    out.accepts = (doc.accepts || []).map((a) => {
      let usd = null;
      try {
        usd = a.amount ? Number(a.amount) / 1e6 : null;
      } catch (e) {}
      return {
        scheme: a.scheme,
        network: a.network,
        asset: a.asset,
        amount_atomic: a.amount,
        amount_usd: usd,
        payTo: a.payTo || a.pay_to,
        maxTimeoutSeconds: a.maxTimeoutSeconds,
      };
    });
  } catch (e) {
    out.decode_error = String(e).slice(0, 200);
  }
  return out;
}

function isBlockedHost(host) {
  return (
    /^(localhost|127\.|0\.|10\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host) ||
    host.endsWith(".local") ||
    host.endsWith(".internal")
  );
}

async function probeTarget(target) {
  let u;
  try {
    u = new URL(target);
  } catch (e) {
    return { ok: false, error: "invalid url" };
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") return { ok: false, error: "unsupported scheme" };
  if (isBlockedHost(u.hostname)) return { ok: false, error: "refusing private host" };
  let res;
  try {
    res = await fetch(u.toString(), { headers: { accept: "application/json" }, redirect: "manual" });
  } catch (e) {
    return { ok: false, error: "fetch failed: " + String(e).slice(0, 150) };
  }
  const hdr =
    res.headers.get("payment-required") ||
    res.headers.get("PAYMENT-REQUIRED") ||
    res.headers.get("x-payment");
  const out = { ok: true, probed_url: u.toString(), status: res.status };
  if (res.status === 402) {
    if (hdr) {
      out.challenge = await decodeChallenge(hdr.replace(/^v2:/, ""));
    } else {
      let txt = "";
      try {
        txt = await res.text();
      } catch (e) {}
      try {
        out.challenge = { x402Version: JSON.parse(txt).x402Version, raw_body: txt.slice(0, 4000) };
      } catch (e) {
        out.challenge = { raw_body: txt.slice(0, 4000) };
      }
    }
  } else {
    out.note = "endpoint did not answer 402, so it is either free or not an x402 resource";
  }
  return out;
}

async function settleVia(payload, requirements) {
  const body = { x402Version: 2, paymentPayload: payload, paymentRequirements: requirements };
  const r = await fetch(FACILITATOR + "/settle", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  let out;
  try {
    out = JSON.parse(text);
  } catch (e) {
    out = { raw: text.slice(0, 500) };
  }
  return { status: r.status, result: out };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const base = url.origin;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

    if (path === "/health") {
      return json({ ok: true, service: "x402-probe", network: NETWORK, price: PRICE, facilitator: FACILITATOR });
    }
    if (path === "/") {
      return json({
        service: "x402-probe",
        paid: PAID,
        free: ["/health", "/.well-known/x402", "/.well-known/x402.json", "/openapi.json"],
        network: NETWORK,
        price: PRICE,
        payTo: PAY_TO,
      });
    }
    if (path === "/.well-known/x402") {
      return json({
        version: 1,
        resources: [base + "/probe?url=https://hermes.swap.io/v1/swap/quote", base + "/price/ETH"],
        ownershipProofs: [PAY_TO],
        instructions:
          "GET /probe?url=<paid-endpoint> returns that endpoint's x402 challenge (price/network/asset/payTo) without paying it. Handles v2 header and v1 JSON-body challenges.",
      });
    }
    if (path === "/.well-known/x402.json" || path === "/.well-known/x402-v2.json") {
      const mk = (p, d) => ({
        resource: base + p,
        type: "http",
        x402Version: 2,
        lastUpdated: new Date().toISOString(),
        accepts: challenge(base + p, d).accepts,
        metadata: { description: d, input: { type: "http", method: "GET" } },
      });
      return json({
        x402Version: 2,
        items: [mk("/probe", PAID["/probe"]), mk("/price/ETH", PAID["/price/ETH"])],
        ownershipProofs: [PAY_TO],
        instructions: "Pay 0.001 USDC on Base per call; retry with the PAYMENT-SIGNATURE header.",
      });
    }
    if (path === "/openapi.json") {
      const op = (id, summary, body) => ({
        operationId: id,
        summary,
        "x-payment-info": { protocols: [{ x402: {} }], price: { mode: "fixed", currency: "USD", amount: "0.001" } },
        requestBody: body,
        responses: { 200: { description: "Result" }, 402: { description: "Payment required" } },
      });
      return json({
        openapi: "3.1.0",
        info: { title: "x402 Probe", version: "1.3.0", contact: { email: "ernest-earnordie@agentmail.to", name: "Ernest", url: "https://earnordie-ernest.github.io/x402-seller-kit/" }, description: "Paid x402 utility API. POST /probe with {url} returns any endpoint's x402 price/network/asset/payTo without paying it. $0.001 USDC on Base per call." },
        servers: [{ url: base }],
        paths: {
          "/probe": {
            post: op("probeEndpoint", "Decode any endpoint's x402 price, network, asset and payTo without paying it. $0.001 USDC on Base.", {
              required: true,
              content: { "application/json": { schema: { type: "object", required: ["url"], properties: { url: { type: "string", format: "uri", description: "https URL of the x402 endpoint to decode" } } } } },
            }),
          },
          "/price/ETH": {
            post: op("ethPrice", "ETH/USD spot price. $0.001 USDC on Base.", {
              required: false,
              content: { "application/json": { schema: { type: "object", properties: { symbol: { type: "string", description: "always ETH" } } } } },
            }),
          },
        },
        "x-discovery": { ownershipProofs: [PAY_TO] },
      });
    }

    // ---- paid routes ----
    const desc = PAID[path];
    if (desc) {
      const payloadHeader = request.headers.get("payment-signature") || request.headers.get("x-payment");
      const ch = challenge(url.toString(), desc);
      if (!payloadHeader) {
        return paymentRequired(ch);
      }
      let payload;
      try {
        payload = b64decode(payloadHeader.replace(/^v2:/, ""));
      } catch (e) {
        return json({ error: "malformed payment payload" }, 402, { "payment-required": b64encode(ch) });
      }
      const reqs = ch.accepts[0];
      const v = await settleVia(payload, reqs);
      const okv = v.result && (v.result.success === true || v.result.settled === true || v.result.valid === true);
      if (v.status !== 200 || !okv) {
        return json({ error: "payment not settled", facilitator: v }, 402, {
          "payment-required": b64encode(ch),
        });
      }
      const receipt = b64encode(v.result);
      let body;
      if (path === "/probe") {
        let target = url.searchParams.get("url");
        if (!target && request.method === "POST") {
          try { target = (await request.clone().json()).url; } catch (e) {}
        }
        body = target ? await probeTarget(target) : { ok: false, error: "missing url (?url= or JSON body {url})" };
      } else {
        let price = null;
        try {
          const r = await fetch("https://api.coinbase.com/v2/prices/ETH-USD/spot");
          price = (await r.json()).data;
        } catch (e) {}
        body = { symbol: "ETH/USD", spot: price, source: "coinbase", at: new Date().toISOString() };
      }
      return json({ paid: true, receipt: v.result, result: body }, 200, { "payment-response": receipt });
    }

    return json({ error: "not found", service: "x402-probe" }, 404);
  },
};
