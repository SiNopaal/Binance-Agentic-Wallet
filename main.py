import sys
import os
import argparse
import asyncio
import json

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from agentic_detector import AgenticDetector
from telegram_listener import TelegramAgenticSniper, HISTORY_FILE, CHANNELS_FILE, load_target_channels
from x_listener import XAgenticHunter
from telethon import TelegramClient
from config import API_ID, API_HASH, SESSION_PATH

async def run_tests():
    print("==================================================================")
    print("🧪 MENJALANKAN UJI COBA DETEKTOR & FILTER AGENTIC AIRDROP")
    print("==================================================================")
    detector = AgenticDetector()

    test_cases = [
        {
            "name": "Case 1: Pesan Singkat Admin Telegram (Garapan AI Agent / BNB Studio)",
            "text": "Mint cepat gasss fee murah: 0x60b9262456de011f7d15a54cdd8c48baaa8b022f"
        },
        {
            "name": "Case 2: Pesan Singkat Admin Telegram (Meme Coin / Spam)",
            "text": "Degen alert pump.fun presale 100x gem beli sekarang solana link"
        },
        {
            "name": "Case 3: Pesan Telegram Khusus Domain .ai / Agent ID",
            "text": "Task Airdrop baru khusus pemegang .ai domain & Binance Agentic Wallet: claim badge airdrop"
        },
        {
            "name": "Case 4: Pesan Airdrop Umum Tanpa AI/Agent",
            "text": "Airdrop bot swap gratis claim 100 token koin baru"
        }
    ]

    for tc in test_cases:
        print(f"\n📌 {tc['name']}")
        print(f"   Input Chat: \"{tc['text']}\"")
        report = await detector.analyze(tc['text'])
        status_icon = "🟢 [LOLOS - AGENTIC TARGET!]" if report['is_agentic'] else "🔴 [DITOLAK - BUKAN AGENTIC]"
        print(f"   Hasil     : {status_icon} (Skor: {report['confidence_score']}%)")
        print("   Alasan    :")
        for r in report['reasons']:
            print(f"      • {r}")

    print("\n==================================================================")
    print("✅ Pengujian Selesai! Filter terbukti membedakan target Agentic vs Spam.")
    print("==================================================================")

async def list_all_user_channels():
    print("==================================================================")
    print("📋 DAFTAR GRUP & CHANNEL TELEGRAM YANG DIIKUTI")
    print("==================================================================")
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    dialogs = await client.get_dialogs(limit=100)
    
    current_whitelist = load_target_channels()
    print(f"File Whitelist: {CHANNELS_FILE}\n")

    count = 0
    for d in dialogs:
        if d.is_channel or d.is_group:
            count += 1
            uname = getattr(d.entity, 'username', None)
            uname_str = f"@{uname}" if uname else "No-Username"
            is_active = (uname and uname.lower() in current_whitelist) or (str(d.entity.id) in current_whitelist)
            status_tag = "🟢 [AKTIF DI-MONITOR]" if is_active else "⚪ [Diabaikan]"
            print(f"[{count:02d}] {status_tag} {d.title} | {uname_str} (ID: {d.entity.id})")

    await client.disconnect()
    print("\n💡 Untuk menambah/mengurangi target, cukup buka & edit file:")
    print(f"   {CHANNELS_FILE}")
    print("==================================================================")

def show_history():
    if not os.path.exists(HISTORY_FILE):
        print("Belum ada riwayat airdrop yang terdeteksi.")
        return
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n📜 Total Garapan Agentic Terdeteksi: {len(data)}")
        for idx, item in enumerate(data[-5:], 1):
            src = item.get("source", "TELEGRAM")
            chan = item.get("channel") or item.get("author") or "Unknown"
            print(f"\n[{idx}] [{src}] {item['timestamp']} | Channel/User: {chan}")
            print(f"    Action: {item['report']['action_type']} | Score: {item['report']['confidence_score']}%")
            if item['report']['contracts']:
                print(f"    Contract: {item['report']['contracts']}")
            print(f"    Message: {item['raw_message'][:100]}...")
    except Exception as e:
        print(f"Error membaca history: {e}")

async def run_both(auto_mint: bool):
    print("==================================================================")
    print("🚀 MENJALANKAN DUAL MONITOR: TELEGRAM (@Nflzxxx) + X (@fannet)")
    print("==================================================================")
    tele_sniper = TelegramAgenticSniper(auto_mint=auto_mint)
    x_sniper = XAgenticHunter(auto_mint=auto_mint)

    await asyncio.gather(
        tele_sniper.start(),
        x_sniper.start()
    )

def main():
    parser = argparse.ArgumentParser(description="Binance Agentic Airdrop Sniper")
    parser.add_argument("--test", action="store_true", help="Uji coba filter deteksi dengan pesan simulasi")
    parser.add_argument("--all", action="store_true", help="Monitor KEDUA-DUANYA: Telegram (@Nflzxxx) + X (@fannet)")
    parser.add_argument("--tele", action="store_true", help="Monitor Telegram (@Nflzxxx) saja")
    parser.add_argument("--x", action="store_true", help="Monitor X/Twitter (@fannet) saja")
    parser.add_argument("--auto-mint", action="store_true", help="Aktifkan eksekusi otomatis ke 3 wallet saat garapan valid terdeteksi")
    parser.add_argument("--history", action="store_true", help="Tampilkan riwayat airdrop yang sudah terdeteksi")
    parser.add_argument("--list-channels", action="store_true", help="Lihat daftar grup Telegram Anda dan status monitornya")
    parser.add_argument("--text", type=str, help="Uji coba deteksi teks spesifik secara manual")

    args = parser.parse_args()

    if args.test:
        asyncio.run(run_tests())
    elif args.list_channels:
        asyncio.run(list_all_user_channels())
    elif args.text:
        detector = AgenticDetector()
        report = asyncio.run(detector.analyze(args.text))
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.history:
        show_history()
    elif args.all:
        asyncio.run(run_both(auto_mint=args.auto_mint))
    elif args.tele:
        sniper = TelegramAgenticSniper(auto_mint=args.auto_mint)
        asyncio.run(sniper.start())
    elif args.x:
        x_sniper = XAgenticHunter(auto_mint=args.auto_mint)
        asyncio.run(x_sniper.start())
    else:
        # Default run both
        asyncio.run(run_both(auto_mint=args.auto_mint))

if __name__ == "__main__":
    main()
