# Binance Agentic Wallet (BAW) Multi-Profile Suite

This module provides profile isolation and session spoofing for running multiple concurrent Binance Agentic Wallet instances on a single machine without authentication conflicts or session invalidation.

---

## 🛠️ The Challenge
By default, the Binance Agentic Wallet CLI (`baw`) stores its auth tokens in the operating system's Credential Vault (Windows Keytar) under a single global service name (`baw`) and relies on the local machine hostname (`os.hostname()`) as the Binance Node Device ID.

When trying to manage multiple wallets:
1. Logging into Account B overwrites the Keytar tokens of Account A.
2. Sharing the same machine hostname causes the Binance backend to identify multiple logins as the same node, terminating previous sessions.

---

## 💡 The Solution: 3-Layer Isolation Architecture

1. **Keytar Vault Isolation (`BINANCE_KEYTAR_SERVICE`)**:
   Each wallet profile uses an isolated credential vault namespace:
   - Profile 1: `baw_acc1`
   - Profile 2: `baw_acc2`
   - Profile 3: `baw_acc3`

2. **Session Storage Directory Isolation (`BINANCE_BAW_DIR`)**:
   Session files, local databases, and temporary caches are separated into:
   - `%USERPROFILE%/.baw/profiles/acc1`
   - `%USERPROFILE%/.baw/profiles/acc2`
   - `%USERPROFILE%/.baw/profiles/acc3`

3. **Node Hostname Spoofing via Preload Hook (`preload.cjs`)**:
   A lightweight Node.js hook injected via `NODE_OPTIONS=--require ...preload.cjs` intercepts `os.hostname()` and assigns a distinct virtual device ID per instance:
   - Profile 1: `Agent-Node-Acc1`
   - Profile 2: `Agent-Node-Acc2`
   - Profile 3: `Agent-Node-Acc3`

---

## 🚀 Quick Setup

Run `setup-profile-commands.bat` to automatically configure:
- `%USERPROFILE%/.baw/` directories and scripts.
- Global wrappers `baw1`, `baw2`, and `baw3` in your `%APPDATA%\npm` path.

### Usage
```bash
# Check status and balance across all accounts
node baw-multi.mjs status

# Login Account 1 via QR Code
baw1 login

# Login Account 2 via QR Code
baw2 login

# Query balances
baw1 wallet balance
baw2 wallet balance
baw3 wallet balance

# Execute contract call from specific wallet
baw1 contract-call preview --binanceChainId 56 --from <ADDR> --to <CONTRACT> --value 0 --inputData <CALLDATA>
```
