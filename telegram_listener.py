import os
import sys
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from config import (
    API_ID,
    API_HASH,
    SESSION_PATH
)
from agentic_detector import AgenticDetector
from executor import MultiWalletExecutor

# Output file for detected airdrops
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "detected_agentic_airdrops.json")
CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_channels.txt")

def load_target_channels() -> set:
    """Membaca daftar whitelist channel target dari target_channels.txt"""
    targets = set()
    if not os.path.exists(CHANNELS_FILE):
        return targets

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Normalize: strip @ and lowercase
            norm = line.lstrip("@").lower()
            targets.add(norm)
    return targets

def save_detected_airdrop(data: dict):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    
    history.append(data)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

class TelegramAgenticSniper:
    def __init__(self, auto_mint: bool = False):
        self.detector = AgenticDetector()
        self.executor = MultiWalletExecutor()
        self.auto_mint = auto_mint
        self.client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
        self.target_channels = load_target_channels()

    def reload_channels(self):
        self.target_channels = load_target_channels()

    def is_channel_whitelisted(self, chat_id, chat_username: str, chat_title: str) -> bool:
        """Cek apakah chat berasal dari channel yang di-whitelist oleh user"""
        if not self.target_channels:
            # Jika file target kosong, default: tolak semua demi keamanan
            return False

        # Cek username
        if chat_username and chat_username.lower().lstrip("@") in self.target_channels:
            return True

        # Cek ID
        if str(chat_id) in self.target_channels or f"-100{chat_id}" in self.target_channels:
            return True

        # Cek judul jika user memasukkan judul persis
        if chat_title and chat_title.lower() in self.target_channels:
            return True

        return False

    async def handle_message(self, event):
        chat = await event.get_chat()
        chat_id = getattr(chat, "id", None)
        chat_title = getattr(chat, "title", "Direct/Group")
        chat_username = getattr(chat, "username", "") or ""

        # FILTER MUTLAK: Hanya proses jika berasal dari Channel Whitelist User!
        if not self.is_channel_whitelisted(chat_id, chat_username, chat_title):
            return

        text = event.message.message or ""
        if not text or len(text.strip()) < 5:
            return

        # Run deep analysis
        report = await self.detector.analyze(text)

        # Print debug log if has potential keywords
        if report["confidence_score"] > 25:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Telegram [@{chat_username or chat_title}] -> Skor: {report['confidence_score']}%")

        # IF VERIFIED AGENTIC AIRDROP
        if report["is_agentic"]:
            print("\n" + "=" * 70)
            print("🚨 [AGENTIC AIRDROP DETECTED DARI GRUP TARGET TELEGRAM!]")
            print("=" * 70)
            print(f"📡 Channel   : {chat_title} (@{chat_username}) [WHITELISTED]")
            print(f"⏰ Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🎯 Action    : {report['action_type']}")
            print(f"⭐ Confidence: {report['confidence_score']}%")
            if report['contracts']:
                print(f"📝 Contracts : {', '.join(report['contracts'])}")
            if report['urls']:
                print(f"🔗 Links     : {', '.join(report['urls'])}")
            print("📋 Verification Reasons:")
            for r in report['reasons']:
                print(f"   • {r}")
            print("=" * 70 + "\n")

            # Save to history log
            save_entry = {
                "source": "TELEGRAM",
                "channel": chat_title,
                "username": chat_username,
                "timestamp": datetime.now().isoformat(),
                "report": report,
                "raw_message": text
            }
            save_detected_airdrop(save_entry)

            # Auto Mint / Execute if enabled
            if self.auto_mint and report["contracts"]:
                target_contract = report["contracts"][0]
                print(f"⚡ [AUTO-MINT ACTIVE] Memicu claim untuk 3 wallet ke {target_contract}...")
                self.executor.execute_contract_call(target_contract)

    async def start(self):
        self.reload_channels()
        await self.client.connect()
        if not await self.client.is_user_authorized():
            print("❌ Error: Telegram session tidak terotorisasi.")
            return

        try:
            me = await self.client.get_me()
            user_display = f"@{me.username}" if getattr(me, "username", None) else getattr(me, "first_name", "Authorized User")
        except Exception:
            user_display = "Authorized User"

        print("==================================================================")
        print("📱 BINANCE AGENTIC AIRDROP SNIPER - TELEGRAM WHITELIST MONITOR")
        print("==================================================================")
        print(f"👤 User Session : {user_display}")
        print(f"🎯 Target File  : {CHANNELS_FILE}")
        print(f"📋 Total Target : {len(self.target_channels)} Grup/Channel Whitelisted")
        for t in list(self.target_channels)[:10]:
            print(f"   • @{t}")
        if len(self.target_channels) > 10:
            print(f"   ... dan {len(self.target_channels) - 10} channel lainnya.")
        print("==================================================================")
        print("🎧 Mendengarkan HANYA grup-grup target terpilih... (Ctrl+C untuk berhenti)\n")

        # Register event handler for incoming messages
        self.client.add_event_handler(self.handle_message, events.NewMessage)

        # Run until disconnected
        await self.client.run_until_disconnected()
