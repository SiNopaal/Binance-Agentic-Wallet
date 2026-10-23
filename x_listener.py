import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from twikit import Client
from config import (
    AGENTIC_KEYWORDS,
    TWITTER_ACCOUNTS_FILE,
    TWITTER_ACCOUNT_NAME,
    TWITTER_AUTH_TOKEN,
    TWITTER_CT0,
    MAX_TWEET_AGE_MINUTES
)
from agentic_detector import AgenticDetector, w3
from security_guard import SecurityGuard
from executor import MultiWalletExecutor
from telegram_listener import save_detected_airdrop

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

SEARCH_QUERIES = [
    '"Binance Agentic Wallet"',
    '"Agent ID" ".ai" airdrop',
    '"BNB Agent" mint OR claim',
    '"Agentic" contract bsc'
]

class XAgenticHunter:
    def __init__(self, auto_mint: bool = False):
        self.detector = AgenticDetector()
        self.security = SecurityGuard(w3=w3)
        self.executor = MultiWalletExecutor()
        self.auto_mint = auto_mint
        self.client = Client('en-US')
        self.seen_tweet_ids = set()
        self.bootstrapped = False

    def load_twitter_account(self):
        """
        Memuat sesi Twitter/X melalui:
        1. Environment variable (TWITTER_AUTH_TOKEN & TWITTER_CT0)
        2. File accounts.json lokal
        """
        if TWITTER_AUTH_TOKEN and TWITTER_CT0:
            self.client.set_cookies({
                "auth_token": TWITTER_AUTH_TOKEN,
                "ct0": TWITTER_CT0
            })
            return {"screen_name": TWITTER_ACCOUNT_NAME or "env_user", "auth_token": TWITTER_AUTH_TOKEN, "ct0": TWITTER_CT0}

        if not os.path.exists(TWITTER_ACCOUNTS_FILE):
            raise FileNotFoundError(
                f"File akun X tidak ditemukan: {TWITTER_ACCOUNTS_FILE}\n"
                f"Silakan atur TWITTER_AUTH_TOKEN & TWITTER_CT0 di file .env atau sediakan accounts.json."
            )

        with open(TWITTER_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        accounts = data.get("accounts", {})
        acc = accounts.get(TWITTER_ACCOUNT_NAME)
        if not acc and accounts:
            first_key = next(iter(accounts))
            acc = accounts[first_key]

        if not acc:
            raise ValueError(f"Akun '{TWITTER_ACCOUNT_NAME}' tidak ditemukan di {TWITTER_ACCOUNTS_FILE}")

        self.client.set_cookies({
            "auth_token": acc["auth_token"],
            "ct0": acc["ct0"]
        })
        return acc

    def load_fannet_account(self):
        return self.load_twitter_account()

    async def bootstrap_cold_start(self):
        """
        COLD-START WARMUP:
        Mengindeks tweet lama yang sudah ada di Twitter sebelum bot hidup.
        Mencegah bot langsung mengeksekusi garapan lama yang kuotanya sudah habis/sold out.
        """
        print("🧊 [COLD-START WARMUP] Mengindeks tweet awal yang sudah ada di X...")
        total_indexed = 0
        for query in SEARCH_QUERIES:
            try:
                tweets = await self.client.search_tweet(query, 'Latest', count=10)
                for tw in tweets:
                    if tw.id not in self.seen_tweet_ids:
                        self.seen_tweet_ids.add(tw.id)
                        total_indexed += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f"   ⚠️ Warmup query notice ({query[:25]}...): {e}")

        self.bootstrapped = True
        print(f"✅ [WARMUP SELESAI] {total_indexed} tweet lama berhasil di-indeks.")
        print(f"🛡️ Freshness Filter Aktif: HANYA tweet berumur <= {MAX_TWEET_AGE_MINUTES} menit yang diproses!\n")

    async def poll_once(self):
        for query in SEARCH_QUERIES:
            try:
                tweets = await self.client.search_tweet(query, 'Latest', count=5)
                for tw in tweets:
                    if tw.id in self.seen_tweet_ids:
                        continue
                    self.seen_tweet_ids.add(tw.id)

                    text = tw.text or ""
                    user = getattr(tw, "user", None)
                    author = getattr(user, "screen_name", "unknown") if user else "unknown"

                    # 0. FRESHNESS GATE (Filter Usia Tweet Maksimal 30 Menit)
                    tw_dt = getattr(tw, "created_at_datetime", None)
                    if tw_dt:
                        if tw_dt.tzinfo is None:
                            tw_dt = tw_dt.replace(tzinfo=timezone.utc)
                        age_seconds = (datetime.now(timezone.utc) - tw_dt).total_seconds()
                        age_minutes = max(0.0, age_seconds / 60.0)
                    else:
                        age_minutes = 0.0

                    is_fresh = age_minutes <= MAX_TWEET_AGE_MINUTES

                    # 1. Analisa Relevansi Agentic
                    report = await self.detector.analyze(text)

                    # 2. Audit Keamanan & Anti-Scam Guard
                    author_audit = self.security.audit_author(user)
                    
                    contract_audits = {}
                    for c in report.get("contracts", []):
                        contract_audits[c] = self.security.audit_contract_safety(c)

                    url_audits = {}
                    for u in report.get("urls", []):
                        url_audits[u] = self.security.audit_url(u)

                    # Jika Lolos Kriteria Agentic
                    if report["is_agentic"]:
                        # Cek apakah ada indikasi drainer / scam
                        is_dangerous = any(ca.get("risk_level") == "CRITICAL / DRAINER" for ca in contract_audits.values())
                        is_untrusted_author = author_audit["trust_level"].startswith("LOW")

                        print("\n" + "=" * 70)
                        if is_dangerous:
                            print("🚨❌ [PERINGATAN: TERDETEKSI INDIKASI SCAM / DRAINER DI X!]")
                        elif not is_fresh:
                            print(f"⏳⚠️ [AGENTIC AIRDROP DITEMUKAN - TWEET KEDALUWARSA ({age_minutes:.1f}m > {MAX_TWEET_AGE_MINUTES}m)]")
                        elif is_untrusted_author:
                            print("⚠️🔍 [AGENTIC AIRDROP DETECTED - PERLU REVIEW (AKUN X BELUM TERPERCAYA)]")
                        else:
                            print("🟢✨ [VERIFIED FRESH AGENTIC AIRDROP DETECTED! (AMAN DARI SCAM)]")
                        print("=" * 70)
                        print(f"👤 Author      : @{author} ({author_audit['followers']} followers | Trust: {author_audit['trust_level']})")
                        print(f"⏰ Usia Tweet  : {age_minutes:.1f} menit lalu (Freshness Limit: {MAX_TWEET_AGE_MINUTES} menit)")
                        print(f"🔗 Tweet URL   : https://x.com/{author}/status/{tw.id}")
                        print(f"🎯 Action      : {report['action_type']}")
                        print(f"⭐ Skor Relevan: {report['confidence_score']}%")
                        
                        if report['contracts']:
                            print(f"📝 Contracts   : {', '.join(report['contracts'])}")
                            for c, ca in contract_audits.items():
                                print(f"   🛡️ Audit [{c[:10]}...]: Risk: {ca['risk_level']} | Aman Auto-Mint: {ca['is_safe_for_automint']}")
                                for blk in ca.get("blocked_reasons", []):
                                    print(f"      ⛔ {blk}")

                        if report['urls']:
                            print(f"🔗 Links       : {', '.join(report['urls'])}")
                            for u, ua in url_audits.items():
                                if ua.get("is_whitelisted"):
                                    print(f"   🛡️ Link Status: 🟢 Whitelist Resmi ({u[:35]}...)")
                                elif ua.get("is_suspicious"):
                                    print(f"   🛡️ Link Status: 🔴 Mencurigakan ({u[:35]}...)")

                        print("📋 Verification Reasons:")
                        for r in report['reasons']:
                            print(f"   • {r}")
                        print("=" * 70 + "\n")

                        # Simpan ke history
                        save_entry = {
                            "source": "X_TWITTER",
                            "author": author,
                            "tweet_url": f"https://x.com/{author}/status/{tw.id}",
                            "tweet_age_minutes": round(age_minutes, 2),
                            "is_fresh": is_fresh,
                            "timestamp": datetime.now().isoformat(),
                            "author_security": author_audit,
                            "contracts_security": contract_audits,
                            "report": report,
                            "raw_message": text
                        }
                        save_detected_airdrop(save_entry)

                        # AUTO-MINT HANYA JIKA FRESH (<= 30 MENIT) & LOLOS AUDIT KEAMANAN!
                        if self.auto_mint and report["contracts"]:
                            target_contract = report["contracts"][0]
                            audit = contract_audits.get(target_contract, {})

                            if not is_fresh:
                                print(f"⛔ [AUTO-MINT DITOLAK: TWEET KEDALUWARSA] Usia tweet {age_minutes:.1f} menit (melebihi filter {MAX_TWEET_AGE_MINUTES} menit). Potensi kuat sudah ludes/sold out!")
                            elif audit.get("is_safe_for_automint") and not is_dangerous and not is_untrusted_author:
                                print(f"⚡ [SECURITY & FRESHNESS PASSED] Tweet fresh ({age_minutes:.1f}m)! Memicu claim aman 3 wallet ke {target_contract}...")
                                self.executor.execute_contract_call(target_contract)
                            else:
                                print(f"⛔ [AUTO-MINT DITAHAN] Kontrak atau akun X belum lolos audit keamanan untuk auto-eksekusi.")

                await asyncio.sleep(4)

            except Exception as e:
                if "429" in str(e):
                    print("⚠️ X Rate limit, jeda 30 detik...")
                    await asyncio.sleep(30)
                else:
                    print(f"X Query Error ({query[:25]}...): {e}")

    async def start(self, interval_seconds: int = 60):
        acc = self.load_twitter_account()
        screen_name = acc.get("screen_name") or TWITTER_ACCOUNT_NAME
        print("==================================================================")
        print("🐦 BINANCE AGENTIC AIRDROP SNIPER - X/TWITTER LIVE MONITOR")
        print("==================================================================")
        print(f"👤 Akun X      : @{screen_name}")
        print(f"🛡️ Security    : ANTI-SCAM, DRAINER GUARD & AUTHOR TRUST ACTIVE")
        print(f"⏱️ Freshness   : MAKSIMAL {MAX_TWEET_AGE_MINUTES} MENIT (Tweet lama ditolak)")
        print(f"⚙️ Auto-Mint   : {'AKTIF (Hanya jika fresh & lolos audit)' if self.auto_mint else 'NONAKTIF'}")
        print(f"🎯 Target      : EKOSISTEM AGENTIC WALLET & .AI REGISTRY")
        print(f"⏱️ Interval    : Setiap {interval_seconds} detik")
        print("==================================================================")

        # Warmup indexing cold-start tweets
        await self.bootstrap_cold_start()

        print("🎧 Memantau tweet baru real-time... (Ctrl+C untuk berhenti)\n")

        while True:
            await self.poll_once()
            await asyncio.sleep(interval_seconds)
