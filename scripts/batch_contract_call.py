#!/usr/bin/env python3
"""
Binance Agentic Wallet Batch Contract Call Template
Simulates preview and executes contract-call across active accounts safely.
"""

import sys
import json
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "core"))

from multi_manager import load_accounts, run_baw_command

def execute_external_call(acc, chain_id, to_addr, input_data, value="0"):
    acc_id = acc.get("id")
    name = acc.get("name")
    
    # 1. Get address
    addr_res = run_baw_command(acc, ["wallet", "address", "--json"])
    if not (addr_res.get("data") and addr_res["data"].get("success")):
        print(f"❌ [Account {acc_id}] Wallet is not connected, skipping.")
        return False, None
        
    addresses = addr_res["data"]["data"].get("addresses", [])
    from_addr = next((a["address"] for a in addresses if str(a.get("binanceChainId")) == str(chain_id)), None)
    if not from_addr:
        from_addr = addresses[0]["address"]
        
    print(f"\n---> [Account {acc_id}: {name}] Calling {to_addr[:10]}... from {from_addr[:10]}...")
    
    # 2. Preview
    cmd_preview = [
        "contract-call", "preview",
        "--binanceChainId", str(chain_id),
        "--from", from_addr,
        "--to", to_addr,
        "--value", str(value),
        "--inputData", input_data,
        "--json"
    ]
    p_res = run_baw_command(acc, cmd_preview, timeout=25)
    p_data = p_res.get("data")
    if not (p_data and p_data.get("success")):
        print(f"❌ Preview failed: {p_data.get('error') if p_data else p_res.get('stderr')}")
        return False, None
        
    req_id = p_data["data"]["requestId"]
    print(f"  ✅ Preview successful. Request ID: {req_id}")
    
    # 3. Execute
    time.sleep(1)
    cmd_exec = ["contract-call", "execute", "--requestId", req_id, "--json"]
    e_res = run_baw_command(acc, cmd_exec, timeout=25)
    e_data = e_res.get("data")
    if e_data and e_data.get("success"):
        tx_hash = e_data["data"].get("txHash")
        print(f"  🚀 BROADCASTED! Tx: {tx_hash}")
        return True, tx_hash
    else:
        print(f"  ❌ Execution failed: {e_data.get('error') if e_data else e_res.get('stderr')}")
        return False, None

def main():
    print("=" * 70)
    print("🚀 BATCH CONTRACT-CALL RUNNER")
    print("=" * 70)
    print("To execute real transactions, configure target contract and calldata.\n")
    
    accounts = load_accounts()
    print(f"Found {len(accounts)} configured accounts.")
    print("Ready to deploy contract calls across active squad wallets.")

if __name__ == "__main__":
    main()
