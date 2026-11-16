#!/usr/bin/env python3
"""
Binance Agentic Wallet Session Backup & Restore Engine
Safely archives and restores local session tokens and Keytar credentials.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT_DIR / "config" / "accounts.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config" / "accounts.example.json"
BACKUP_DIR = Path(os.path.expanduser("~/.baw/backups")).resolve()

def get_node_keytar_helper():
    """Returns JavaScript code snippet to read/write Keytar credentials cleanly."""
    return """
const keytar = require(process.argv[2]);
const action = process.argv[3];
const service = process.argv[4];
const account = process.argv[5];
const value = process.argv[6];

async function run() {
    try {
        if (action === 'get') {
            const pwd = await keytar.getPassword(service, account);
            console.log(pwd || '');
        } else if (action === 'set') {
            await keytar.setPassword(service, account, value);
            console.log('OK');
        }
    } catch (e) {
        process.stderr.write(e.message);
        process.exit(1);
    }
}
run();
"""

def find_keytar_path():
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@binance/agentic-wallet/node_modules/@github/keytar",
        Path("/usr/local/lib/node_modules/@binance/agentic-wallet/node_modules/@github/keytar"),
        Path(os.path.expanduser("~/.nvm/versions/node"))
    ]
    for c in candidates:
        if c.exists():
            return str(c).replace("\\", "/")
    return "@github/keytar"

def call_keytar(action, service, account="agentSessionId", value=""):
    keytar_path = find_keytar_path()
    script = get_node_keytar_helper()
    cmd = ["node", "-e", script, keytar_path, action, service, account, value]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return res.stdout.strip()

def backup_sessions():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    with open(target, 'r', encoding='utf-8') as f:
        accounts = json.load(f).get("accounts", [])
        
    print(f"📦 Starting session backup to: {BACKUP_DIR}\n")
    for acc in accounts:
        acc_id = acc.get("id")
        service = acc.get("service", f"baw_acc{acc_id}")
        profile_dir = Path(acc.get("profile_dir", os.path.expanduser(f"~/.baw/profiles/acc{acc_id}"))).resolve()
        
        acc_backup_dir = BACKUP_DIR / f"account{acc_id}_{acc.get('name')}"
        acc_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Backup session.json
        session_file = profile_dir / "session.json"
        if session_file.exists():
            shutil.copy2(session_file, acc_backup_dir / "session.json")
            print(f"  ✅ [Account {acc_id}] session.json backed up.")
        else:
            print(f"  ⚠️ [Account {acc_id}] session.json not found in profile.")
            
        # 2. Backup Keytar credential
        session_id = call_keytar("get", service, "agentSessionId")
        if session_id:
            with open(acc_backup_dir / "keytar_session.txt", "w", encoding="utf-8") as f:
                f.write(session_id.strip())
            print(f"  ✅ [Account {acc_id}] Keytar secret backed up: {session_id[:8]}...")
        else:
            print(f"  ⚠️ [Account {acc_id}] No Keytar token found for service {service}")
            
    print("\n🏁 Backup routine finished successfully.")

def restore_sessions():
    if not BACKUP_DIR.exists():
        print(f"❌ Backup directory {BACKUP_DIR} does not exist.")
        return
        
    target = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    with open(target, 'r', encoding='utf-8') as f:
        accounts = json.load(f).get("accounts", [])
        
    print(f"♻️ Restoring BAW sessions from: {BACKUP_DIR}\n")
    for acc in accounts:
        acc_id = acc.get("id")
        service = acc.get("service", f"baw_acc{acc_id}")
        profile_dir = Path(acc.get("profile_dir", os.path.expanduser(f"~/.baw/profiles/acc{acc_id}"))).resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        acc_backup_dir = BACKUP_DIR / f"account{acc_id}_{acc.get('name')}"
        if not acc_backup_dir.exists():
            # Try wildcards
            matches = list(BACKUP_DIR.glob(f"account{acc_id}_*"))
            if matches:
                acc_backup_dir = matches[0]
                
        if not acc_backup_dir.exists():
            print(f"  ⚠️ [Account {acc_id}] No backup directory found.")
            continue
            
        # Restore session.json
        b_session = acc_backup_dir / "session.json"
        if b_session.exists():
            shutil.copy2(b_session, profile_dir / "session.json")
            print(f"  ✅ [Account {acc_id}] session.json restored.")
            
        # Restore Keytar
        b_keytar = acc_backup_dir / "keytar_session.txt"
        if b_keytar.exists():
            with open(b_keytar, "r", encoding="utf-8") as f:
                token = f.read().strip()
            if token:
                res = call_keytar("set", service, "agentSessionId", token)
                if res == "OK":
                    print(f"  ✅ [Account {acc_id}] Keytar token restored into {service}.")
                else:
                    print(f"  ❌ [Account {acc_id}] Failed to restore Keytar token.")
                    
    print("\n🏁 Restore routine finished. Run `python core/multi_manager.py --status` to verify.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_sessions()
    else:
        backup_sessions()
