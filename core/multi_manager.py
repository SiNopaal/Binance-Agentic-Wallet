#!/usr/bin/env python3
"""
Binance Agentic Wallet (BAW) Multi-Account Manager
Coordinates, executes, and monitors multiple isolated BAW profiles concurrently.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT_DIR / "config" / "accounts.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config" / "accounts.example.json"
PRELOAD_PATH = (ROOT_DIR / "core" / "preload.cjs").resolve()

def load_accounts():
    target = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    if not target.exists():
        print(f"❌ Configuration file not found at {target}")
        sys.exit(1)
    with open(target, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("accounts", [])

def get_account_env(acc, base_dir=None):
    acc_id = acc.get("id")
    profile_dir = Path(acc.get("profile_dir", os.path.expanduser(f"~/.baw/profiles/acc{acc_id}"))).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    env["BINANCE_BAW_DIR"] = str(profile_dir)
    env["BINANCE_KEYTAR_SERVICE"] = acc.get("service", f"baw_acc{acc_id}")
    env["BINANCE_DEVICE_NAME"] = acc.get("device_name", f"Agent-Node-Acc{acc_id}")
    env["BINANCE_INSTANCE_ID"] = acc.get("instance_id", "28:92:00:6c:9e:0e")
    
    if PRELOAD_PATH.exists():
        safe_path = str(PRELOAD_PATH).replace("\\", "/")
        env["NODE_OPTIONS"] = f'--require "{safe_path}"'
        
    return env

def run_baw_command(acc, args, timeout=30):
    env = get_account_env(acc)
    cmd = ["baw"] + args
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout, shell=(os.name == 'nt'))
        try:
            parsed = json.loads(res.stdout) if "--json" in args else None
        except Exception:
            parsed = None
        return {
            "account_id": acc.get("id"),
            "name": acc.get("name"),
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "data": parsed
        }
    except Exception as e:
        return {
            "account_id": acc.get("id"),
            "name": acc.get("name"),
            "success": False,
            "error": str(e)
        }

def check_all_status(accounts):
    print("=" * 85)
    print("🤖 BINANCE AGENTIC WALLET (BAW) - MULTI-ACCOUNT STATUS AUDIT")
    print("=" * 85)
    print(f"{'ID':<4} | {'Name':<18} | {'Status':<14} | {'BSC Address':<42}")
    print("-" * 85)
    
    def check_single(acc):
        status_res = run_baw_command(acc, ["wallet", "status", "--json"], timeout=15)
        is_connected = False
        if status_res.get("data") and status_res["data"].get("success"):
            is_connected = status_res["data"].get("data", {}).get("status") == "CONNECTED"
            
        addr = "Not Connected"
        if is_connected:
            addr_res = run_baw_command(acc, ["wallet", "address", "--json"], timeout=15)
            if addr_res.get("data") and addr_res["data"].get("success"):
                addresses = addr_res["data"].get("data", {}).get("addresses", [])
                bsc = next((a["address"] for a in addresses if a.get("chainName") == "BSC"), None)
                if bsc:
                    addr = bsc
        return acc.get("id"), acc.get("name"), is_connected, addr

    with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
        results = list(executor.map(check_single, accounts))
        
    results.sort(key=lambda x: x[0])
    for acc_id, name, is_conn, addr in results:
        status_str = "🟢 CONNECTED" if is_conn else "🔴 UNCONNECTED"
        print(f"{acc_id:<4} | {name:<18} | {status_str:<14} | {addr:<42}")
    print("=" * 85)

def main():
    parser = argparse.ArgumentParser(description="BAW Multi-Account Manager CLI")
    parser.add_argument("--status", action="store_true", help="Audit connection status for all accounts")
    parser.add_argument("--run", nargs=argparse.REMAINDER, help="Execute arbitrary BAW command across all accounts")
    parser.add_argument("--acc", type=int, help="Target specific account ID (optional)")
    
    args = parser.parse_args()
    accounts = load_accounts()
    
    if args.acc:
        accounts = [a for a in accounts if a.get("id") == args.acc]
        if not accounts:
            print(f"❌ Account ID {args.acc} not found in configuration.")
            sys.exit(1)
            
    if args.status or not args.run:
        check_all_status(accounts)
    elif args.run:
        print(f"🚀 Executing across {len(accounts)} accounts: baw {' '.join(args.run)}\n")
        for acc in accounts:
            print(f"--- [Account {acc.get('id')}: {acc.get('name')}] ---")
            res = run_baw_command(acc, args.run)
            print(res.get("stdout") or res.get("stderr") or res.get("error"))
            print()

if __name__ == "__main__":
    main()
