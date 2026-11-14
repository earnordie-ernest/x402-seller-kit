# Go-live checklist — x402 seller

- [ ] `PAY_TO` is an address whose key you control (PUT your own; never a placeholder).
- [ ] Test on `eip155:84532` (Base Sepolia) before `eip155:8453` (mainnet).
- [ ] Confirm `curl -i` returns **402** with sane `accepts` for your unpaid route.
- [ ] Expose a public URL (cloudflared/ngrok) and re-check 402 from outside.
- [ ] Make one real $0.001 call from a funded wallet; confirm USDC lands in `PAY_TO`.
- [ ] Keep a free `/health` route for uptime monitors.
- [ ] Do real work only inside the paid handler (it runs after settlement).
- [ ] Log each settled payment (tx hash, payer, amount) for your records.
- [ ] Price per request low enough that agents pay without thinking ($0.0005–$0.01).
