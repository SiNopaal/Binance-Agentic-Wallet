#!/usr/bin/env python3
"""
Binance Agentic Wallet 24/7 Keep-Alive & Auto-Recovery Daemon
Monitors connection status, records heartbeats, and triggers recovery on disconnects.
"""

import os
import sys
import time
import json
import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "core"))

from multi_manager import load_accounts, run_baw_command
from session_backup_restore import restore_sessions

LOG_PATH = ROOT_DIR / "baw_keepalive.log"
ALERT_PATH = ROOT_DIR / "keepalive_alert.txt"

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def ping_cycle(accounts):
    log("💓 [Heartbeat] Running wallet connection check across all accounts...")
    disconnected = []
    
    for acc in accounts:
        acc_id = acc.get("id")
        name = acc.get("name")
        res = run_baw_command(acc, ["wallet", "address", "--json"], timeout=20)
        
        if res.get("data") and res["data"].get("success"):
            addresses = res["data"].get("data", {}).get("addresses", [])
            bsc = next((a["address"] for a in addresses if a.get("chainName") == "BSC"), "Connected")
            log(f"   ✅ [Account {acc_id}: {name}] ACTIVE: {bsc}")
        else:
            err = "UNKNOWN"
            if res.get("data") and res["data"].get("error"):
                err = res["data"]["error"].get("name", "DISCONNECTED")
            elif res.get("error"):
                err = res.get("error")
            log(f"   ⚠️ [Account {acc_id}: {name}] EXPIRED/DISCONNECTED: {err}")
            disconnected.append((acc, err))
            
    if disconnected:
        alert_msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DISCONNECT DETECTED:\n"
        for acc, err in disconnected:
            alert_msg += f"Account {acc.get('id')} ({acc.get('name')}): {err}\n"
        with open(ALERT_PATH, "w", encoding="utf-8") as f:
            f.write(alert_msg)
        log(f"🚨 {len(disconnected)} account(s) disconnected! Attempting auto-restore from backups...")
        try:
            restore_sessions()
        except Exception as e:
            log(f"❌ Auto-restore failed: {e}")
    else:
        if ALERT_PATH.exists():
            try:
                ALERT_PATH.unlink()
            except Exception:
                pass

def main():
    log("🚀 BAW 24/7 AUTO KEEP-ALIVE DAEMON STARTED")
    accounts = load_accounts()
    log(f"Loaded {len(accounts)} account(s) to monitor.")
    
    interval = int(os.environ.get("BAW_KEEPALIVE_INTERVAL", 1200)) # Default 20 minutes
    while True:
        try:
            ping_cycle(accounts)
        except Exception as e:
            log(f"❌ Error during heartbeat loop: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    main()
