#!/usr/bin/env python3
"""
Binance Agentic Wallet Batch Balance Auditor
Fetches native gas balances and token holdings across all connected accounts.
"""

import sys
import json
import urllib.request
import ssl
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "core"))

from multi_manager import load_accounts, run_baw_command

RPC_URL = "https://bsc-dataseed1.defibit.io"
ctx = ssl._create_unverified_context()

def rpc_call(method, params):
    try:
        req = urllib.request.Request(
            RPC_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        )
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            return json.loads(r.read().decode()).get("result")
    except Exception:
        return None

def get_onchain_bnb_balance(address):
    res = rpc_call("eth_getBalance", [address, "latest"])
    if res and res != "0x":
        return int(res, 16) / 1e18
    return 0.0

def main():
    accounts = load_accounts()
    print("=" * 80)
    print("💰 BAW SQUAD BATCH BALANCE AUDITOR (BSC MAINNET)")
    print("=" * 80)
    print(f"{'ID':<4} | {'Name':<18} | {'Native BNB':<14} | {'Address':<42}")
    print("-" * 80)
    
    total_bnb = 0.0
    for acc in accounts:
        acc_id = acc.get("id")
        name = acc.get("name")
        res = run_baw_command(acc, ["wallet", "address", "--json"], timeout=15)
        
        addr = "Not Connected"
        bnb_bal = 0.0
        if res.get("data") and res["data"].get("success"):
            addresses = res["data"].get("data", {}).get("addresses", [])
            bsc = next((a["address"] for a in addresses if a.get("chainName") == "BSC"), None)
            if bsc:
                addr = bsc
                bnb_bal = get_onchain_bnb_balance(bsc)
                total_bnb += bnb_bal
                
        bal_str = f"{bnb_bal:.6f} BNB" if addr != "Not Connected" else "—"
        print(f"{acc_id:<4} | {name:<18} | {bal_str:<14} | {addr:<42}")
        
    print("=" * 80)
    print(f"🔥 TOTAL PORTFOLIO BALANCE: {total_bnb:.6f} BNB")
    print("=" * 80)

if __name__ == "__main__":
    main()
