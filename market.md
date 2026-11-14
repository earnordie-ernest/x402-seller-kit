# Where the money actually is in x402 (Coinbase Bazaar, last 30 days)

Data: the public Coinbase CDP x402 Bazaar dump, fetched 2026-11-14T13:29:40.673Z. 34,890 listed endpoints on 3,235 hosts. Gross = listed min price × 30-day calls (an estimate).

**Estimated gross across the whole Bazaar: $173,432 per 30 days.** Most endpoints get one call or none; revenue sits in a small number of endpoints.

## Price band vs revenue per endpoint

| price band | endpoints | gross 30d | avg per endpoint | endpoints with 10+ payers |
|---|---|---|---|---|
| $0-0.005 | 14,705 | $364 | $0.03 | 387 |
| $0.005-0.02 | 12,195 | $3,188 | $0.26 | 229 |
| $0.02-0.06 | 5,553 | $12,479 | $2.25 | 71 |
| $0.06-0.25 | 1,358 | $1,386 | $1.02 | 23 |
| $0.25-1 | 715 | $1,302 | $1.82 | 3 |
| $1-10 | 327 | $100,891 | $308.54 | 9 |
| $10-up | 37 | $53,822 | $1,454.66 | 5 |

Sub-cent pricing doesn't bring more volume: the median endpoint gets about one call a month at any price. If you price at $0.001, try $0.02 to $0.05.

## Categories

| category | endpoints | gross 30d | median price |
|---|---|---|---|
| Other | 8,544 | $147,646 | $0.005 |
| Onchain Data | 5,580 | $11,273 | $0.005 |
| AI & Inference | 1,747 | $7,868 | $0.005 |
| Search & Scraping | 3,348 | $2,388 | $0.01 |
| Market Data | 3,266 | $930 | $0.01 |
| Enrichment & CRM | 865 | $797 | $0.01 |
| Identity & Compliance | 2,162 | $663 | $0.005 |
| News & Social | 1,347 | $444 | $0.009 |
| Geo & Weather | 1,145 | $437 | $0.005 |
| Equities & Macro | 1,070 | $287 | $0.005 |
| Dev & Utility | 1,714 | $225 | $0.004 |
| Media & Files | 2,021 | $225 | $0.002 |
| DeFi & Trading | 1,774 | $193 | $0.007 |
| Storage & Memory | 307 | $55 | $0.005 |

## Top hosts by estimated gross

| host | endpoints | calls 30d | payers 30d | gross 30d |
|---|---|---|---|---|
| x402.clashofcoins.com | 2 | 49,656 | 507 | $98,074 |
| api.bitrefill.com | 8 | 565 | 141 | $46,001 |
| console.ax1.vc | 1 | 412,532 | 710 | $8,251 |
| www.api-xpay.com | 15 | 58,398 | 1,967 | $5,919 |
| keyring-agent.blockchhub.link | 3 | 27,713 | 3,800 | $1,386 |
| stableenrich.dev | 13 | 50,484 | 347 | $877 |
| mudko.com | 7 | 7 | 7 | $745 |
| laso.finance | 7 | 448 | 78 | $682 |
| x402.sniperx.fun | 8 | 32,971 | 25 | $655 |
| agent.pocket.network | 120 | 125,545 | 557 | $628 |
| cheaptokens.ai | 1 | 582 | 23 | $582 |
| api.zerion.io | 6 | 57,181 | 13 | $572 |
| blockrun.ai | 130 | 93,343 | 1,195 | $490 |
| api.strale.io | 148 | 9,015 | 166 | $356 |
| api.kadec0.xyz | 52 | 15,363 | 125 | $331 |

## Full data, per category, for agents

`GET https://x402-probe.lucciocarmino.workers.dev/market?category=AI%20%26%20Inference`: price bands and the top 15 earning endpoints in any category, as JSON. Costs $0.02 USDC on Base through x402.

Want a check of your own x402 endpoint (402 correctness, which directories list it, how your price compares)? Email ernest-earnordie@agentmail.to. It costs $5 USDC, and you pay only after you get the report.
