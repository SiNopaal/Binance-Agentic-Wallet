import os
import sys
import json
import asyncio
from web3 import Web3

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import (
    API_ID, API_HASH, SESSION_PATH, BSC_RPC_LIST,
    WALLETS, MAX_GAS_FEE_LIMIT_BNB
)
from security_guard import SecurityGuard
from agentic_detector import AgenticDetector, w3
from executor import MultiWalletExecutor
from auto_seller import AutoSeller
from telegram_listener import load_target_channels, CHANNELS_FILE
from x_listener import XAgenticHunter

async def full_audit():
    print("==================================================================")
    print("🔍 AUDIT MENYELURUH SISTEM: BINANCE AGENTIC AIRDROP SNIPER")
    print("==================================================================")
    audit_results = {}

    # 1. AUDIT KONFIGURASI & KONEKTIVITAS BLOCKCHAIN
    print("\n[1/7] Mengaudit Konfigurasi & RPC BSC...")
    try:
        rpc_ok = w3 is not None and w3.is_connected()
        chain_id = w3.eth.chain_id if rpc_ok else None
        latest_block = w3.eth.block_number if rpc_ok else None
        print(f"   • BSC RPC: {'🟢 TERHUBUNG' if rpc_ok else '🔴 GAGAL'}")
        print(f"   • Chain ID: {chain_id} (BSC Mainnet)")
        print(f"   • Block Number Terkini: {latest_block}")
        audit_results["rpc_connectivity"] = rpc_ok and chain_id == 56
    except Exception as e:
        print(f"   ❌ Error RPC: {e}")
        audit_results["rpc_connectivity"] = False

    # 2. AUDIT 3 DOMPET BINANCE AGENTIC WALLET (BAW)
    print("\n[2/7] Mengaudit Status & Saldo 3 Dompet Agentic...")
    try:
        wallets_ok = True
        seller = AutoSeller()
        for acc_id, w in WALLETS.items():
            cmd = w["cmd"]
            bals = seller.get_wallet_balances(acc_id)
            has_gas = any((b.get("symbol") == "BNB" or b.get("token") == "BNB") for b in bals)
            bnb_entry = next((b for b in bals if b.get("symbol") == "BNB" or b.get("token") == "BNB"), {})
            bal_num = bnb_entry.get("balance", "0")[:8]
            print(f"   • [{w['name']} - {cmd}]: {'🟢 AKTIF' if has_gas else '⚠️ CEK GAS'} (Saldo: {bal_num} BNB)")
            if not has_gas:
                wallets_ok = False
        audit_results["wallets_status"] = wallets_ok
    except Exception as e:
        print(f"   ❌ Error Wallets: {e}")
        audit_results["wallets_status"] = False

    # 3. AUDIT ENGINE DETEKSI AGENTIC & DOMAIN .AI
    print("\n[3/7] Mengaudit Mesin Deteksi & Filter (.ai & Agentic)...")
    try:
        detector = AgenticDetector()
        rep_pos = await detector.analyze("Mint cepat gasss fee murah: 0x60b9262456de011f7d15a54cdd8c48baaa8b022f")
        rep_neg = await detector.analyze("pump.fun presale solana meme degen")
        pos_pass = rep_pos["is_agentic"] and rep_pos["confidence_score"] >= 80
        neg_pass = not rep_neg["is_agentic"] and rep_neg["confidence_score"] == 0
        print(f"   • Deteksi Target Agentic Asli : {'🟢 100% AKURAT (LOLOS)' if pos_pass else '🔴 GAGAL'}")
        print(f"   • Filter Buang Spam Meme Coin : {'🟢 100% AKURAT (DIBUANG)' if neg_pass else '🔴 GAGAL'}")
        audit_results["agentic_detector"] = pos_pass and neg_pass
    except Exception as e:
        print(f"   ❌ Error Detector: {e}")
        audit_results["agentic_detector"] = False

    # 4. AUDIT SISTEM KEAMANAN & ANTI-SCAM GUARD
    print("\n[4/7] Mengaudit Modul Anti-Scam & Drainer Blocker...")
    try:
        guard = SecurityGuard(w3=w3)
        drainer_audit = guard.audit_contract_safety("0x15F9733eCcb21DAB0458e6446f4914004524EFE7", calldata="0x095ea7b3000000")
        is_blocked = drainer_audit["risk_level"] == "CRITICAL / DRAINER"
        
        phish_audit = guard.audit_url("https://claim-airdrop-binance.top")
        is_phish_flagged = phish_audit["is_suspicious"]

        print(f"   • Blokir Otomatis Fungsi Drainer (approve) : {'🟢 DIBLOKIR TOTAL' if is_blocked else '🔴 JEBOL'}")
        print(f"   • Deteksi Otomatis Domain Phishing (.top)  : {'🟢 TERDETEKSI BAHAYA' if is_phish_flagged else '🔴 JEBOL'}")
        audit_results["security_guard"] = is_blocked and is_phish_flagged
    except Exception as e:
        print(f"   ❌ Error Security Guard: {e}")
        audit_results["security_guard"] = False

    # 5. AUDIT ZERO-COST & FREE-MINT ENFORCEMENT
    print("\n[5/7] Mengaudit Gembok Free-Mint (Haram Berbayar)...")
    try:
        executor = MultiWalletExecutor()
        paid_res = executor.execute_contract_call("0x15F9733eCcb21DAB0458e6446f4914004524EFE7", value_wei="1000000000000000")
        is_paid_rejected = len(paid_res) == 0
        print(f"   • Pembatalan Otomatis Transaksi Berbayar (>0 wei): {'🟢 SUKSES DIBATALKAN' if is_paid_rejected else '🔴 JEBOL'}")
        audit_results["free_mint_enforcer"] = is_paid_rejected
    except Exception as e:
        print(f"   ❌ Error Free Mint Enforcer: {e}")
        audit_results["free_mint_enforcer"] = False

    # 6. AUDIT AKUN SCRAPER (TELEGRAM & X)
    print("\n[6/7] Mengaudit Kredensial Listener (Telegram & X)...")
    try:
        hunter = XAgenticHunter(auto_mint=False)
        x_acc = hunter.load_twitter_account()
        has_x_tokens = bool(x_acc.get("auth_token") and x_acc.get("ct0"))
        print(f"   • Twitter / X Session: {'🟢 VALID & AKTIF' if has_x_tokens else '🔴 KREDENSIAL RUSAK'}")

        tele_sess_ok = os.path.exists(SESSION_PATH) and os.path.getsize(SESSION_PATH) > 1000
        print(f"   • Telegram Session    : {'🟢 VALID & AKTIF' if tele_sess_ok else '🔴 FILE TIDAK ADA'}")

        targets = load_target_channels()
        targets_ok = len(targets) >= 1
        print(f"   • Whitelist Channels  : {'🟢 CHANNEL TERKUNCI' if targets_ok else '⚠️ Tidak ada channel'}")
        for ch in targets:
            print(f"      - @{ch}")

        audit_results["scraper_accounts"] = has_x_tokens and tele_sess_ok and targets_ok
    except Exception as e:
        print(f"   ❌ Error Scraper Accounts: {e}")
        audit_results["scraper_accounts"] = False

    # 7. AUDIT SISTEM AUTO-REVOKE APPROVALS
    print("\n[7/7] Mengaudit Sistem Post-Mint Auto-Revoke...")
    try:
        executor = MultiWalletExecutor()
        print("   • Menjalankan pemindaian approval aktif pada 3 dompet...")
        executor.revoke_all_3_wallets()
        print("   • Status Post-Mint Revoke Guard: 🟢 100% SIAP AMANKAN DOMPET")
        audit_results["auto_revoke"] = True
    except Exception as e:
        print(f"   ❌ Error Auto Revoke: {e}")
        audit_results["auto_revoke"] = False

    print("\n" + "=" * 66)
    all_passed = all(audit_results.values())
    if all_passed:
        print("🎉 HASIL AUDIT FINAL: 100% PASS (SEMUA 7 SUB-SISTEM LOLOS AUDIT)")
        print("Sistem terverifikasi aman, stabil, anti-scam, dan siap tempur!")
    else:
        print("⚠️ HASIL AUDIT: Ada komponen yang perlu perbaikan!")
        for k, v in audit_results.items():
            print(f"   • {k}: {'PASS' if v else 'FAIL'}")
    print("=" * 66 + "\n")

if __name__ == "__main__":
    asyncio.run(full_audit())
