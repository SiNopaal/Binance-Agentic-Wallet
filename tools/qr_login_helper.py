#!/usr/bin/env python3
"""
Binance Agentic Wallet Interactive QR Login Helper
Simplifies profile authentication, displays QR codes, and backs up credentials upon success.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "core"))

from multi_manager import load_accounts, get_account_env
from session_backup_restore import call_keytar

QR_DIR = ROOT_DIR / "qr_codes"
BACKUP_DIR = Path(os.path.expanduser("~/.baw/backups")).resolve()

def generate_qr_image(url, out_path):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        return True
    except ImportError:
        # Fallback to ASCII in terminal
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except Exception:
            pass
        return False

def login_account(acc):
    acc_id = acc.get("id")
    name = acc.get("name")
    env = get_account_env(acc)
    profile_dir = Path(env["BINANCE_BAW_DIR"]).resolve()
    service = env["BINANCE_KEYTAR_SERVICE"]
    
    print("\n" + "=" * 70)
    print(f"🔑 INITIATING LOGIN FOR ACCOUNT #{acc_id}: {name}")
    print(f"📁 Profile Directory : {profile_dir}")
    print(f"🔐 Keytar Service   : {service}")
    print("=" * 70)
    
    # 1. Run auth signin
    cmd_signin = ["baw", "auth", "signin", "--json"]
    print("[*] Requesting pairing code from Binance Web3...")
    res = subprocess.run(cmd_signin, env=env, capture_output=True, text=True, shell=(os.name == 'nt'))
    
    try:
        data = json.loads(res.stdout)
    except Exception:
        print(f"❌ Failed to parse response: {res.stdout}\n{res.stderr}")
        return False
        
    if not data.get("success"):
        err = data.get("error", {})
        print(f"❌ Sign-in failed: {err.get('message', 'Unknown error')}")
        return False
        
    login_data = data.get("data", {})
    if login_data.get("status") == "ALREADY_CONNECTED":
        print(f"✅ Account #{acc_id} is already connected!")
        return True
        
    url = login_data.get("urlForWeb")
    code = login_data.get("pairingCode")
    qr_id = login_data.get("qrCodeId")
    
    QR_DIR.mkdir(parents=True, exist_ok=True)
    qr_file = QR_DIR / f"account{acc_id}_{name}_qr.png"
    has_img = generate_qr_image(url, qr_file)
    
    print("\n" + "─" * 70)
    print(f"👉 VERIFY IN BINANCE WALLET APP")
    print(f"🔢 PAIRING CODE : \033[1;33m{code}\033[0m (Make sure numbers match!)")
    print(f"🔗 DIRECT URL    : {url}")
    if has_img:
        print(f"🖼️ QR IMAGE FILE: {qr_file}")
    print("─" * 70)
    print("\n⏳ Waiting for scan and confirmation in Binance App (Max 5 mins)...")
    
    # 2. Run blocking auth verify
    cmd_verify = ["baw", "auth", "verify", "--qrCodeId", qr_id, "--json"]
    verify_res = subprocess.run(cmd_verify, env=env, capture_output=True, text=True, shell=(os.name == 'nt'))
    
    try:
        v_data = json.loads(verify_res.stdout)
    except Exception:
        v_data = {}
        
    if v_data.get("success") and v_data.get("data", {}).get("status") == "SUCCESS":
        print(f"\n🎉 SUCCESS: Account #{acc_id} ({name}) is now CONNECTED!")
        
        # 3. Create immediate backup
        acc_backup_dir = BACKUP_DIR / f"account{acc_id}_{name}"
        acc_backup_dir.mkdir(parents=True, exist_ok=True)
        session_file = profile_dir / "session.json"
        if session_file.exists():
            import shutil
            shutil.copy2(session_file, acc_backup_dir / "session.json")
        session_id = call_keytar("get", service, "agentSessionId")
        if session_id:
            with open(acc_backup_dir / "keytar_session.txt", "w", encoding="utf-8") as f:
                f.write(session_id.strip())
        print(f"💾 Session credentials automatically backed up to {acc_backup_dir}")
        return True
    else:
        err = v_data.get("error", {}).get("message", verify_res.stderr or "Verification timeout")
        print(f"\n❌ Login verification failed: {err}")
        return False

def main():
    parser = argparse.ArgumentParser(description="BAW QR Login Helper")
    parser.add_argument("--acc", type=int, required=True, help="Account ID to sign into")
    args = parser.parse_args()
    
    accounts = load_accounts()
    target = next((a for a in accounts if a.get("id") == args.acc), None)
    if not target:
        print(f"❌ Account ID {args.acc} not found in accounts.json")
        sys.exit(1)
        
    login_account(target)

if __name__ == "__main__":
    main()
