import os
import sys
from dotenv import load_dotenv

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Telegram Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
SESSION_PATH = os.getenv("TELEGRAM_SESSION_PATH", os.path.join(BASE_DIR, "session", "user.session"))

# Twitter / X Configuration
TWITTER_ACCOUNTS_FILE = os.getenv("TWITTER_ACCOUNTS_FILE", os.path.join(BASE_DIR, "accounts.json"))
TWITTER_ACCOUNT_NAME = os.getenv("TWITTER_ACCOUNT_NAME", "fannettt")
TWITTER_AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN", "")
TWITTER_CT0 = os.getenv("TWITTER_CT0", "")

# Tweet & Post Freshness Limit in Minutes (Default: 30 minutes)
# Tweet lebih tua dari batas ini otomatis ditolak auto-mint demi menghindari kuota sold-out!
MAX_TWEET_AGE_MINUTES = int(os.getenv("MAX_TWEET_AGE_MINUTES", "30"))

# BSC RPC Endpoints (with fallback)
BSC_RPC_LIST = [
    os.getenv("BSC_RPC_ENDPOINT", "https://bsc-dataseed.binance.org"),
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed1.ninicoin.io",
    "https://binance.llamarpc.com"
]

# Known Agentic / Agent ID Master Registry contracts on BSC (Chain 56)
AGENTIC_REGISTRIES = [
    "0x60b9262456de011f7d15a54cdd8c48baaa8b022f",
    "0x0000000000000000000000000000000000000000"
]

# Agentic Specific Keywords (Weights for detection)
AGENTIC_KEYWORDS = {
    "high": [
        "agentic", "binance agentic", "agent wallet", "agentid", "agent id",
        ".ai domain", "agent studio", "bnb agent", "x402", "erc-6551",
        "autonomous agent", "agent contract", "ai agent airdrop"
    ],
    "medium": [
        "agent", ".ai", "ai mint", "ai token", "virtuals", "elizaos",
        "spectral", "fetch.ai", "bstock", "ai grant", "prompt", "llm"
    ],
    "action": [
        "free mint", "free airdrop", "free claim", "claim free", "mint free",
        "free", "zero cost", "airdrop", "whitelist", "wl", "badge"
    ]
}

# Negative Keywords (AUTO-REJECT: Paid mints, presale, sold-out, casino, meme coin spam)
# STRICT ZERO-COST & FRESHNESS RULE:
NEGATIVE_KEYWORDS = [
    # Sold out & Ended signals
    "sold out", "soldout", "all minted", "mint ended", "claim ended", "mint closed", "whitelist closed",
    # Paid Mint & Sales Traps
    "paid mint", "mint price", "mint fee:", "price:", "cost:", "buy ticket",
    "0.01 bnb", "0.02 bnb", "0.03 bnb", "0.05 bnb", "0.1 bnb", "0.2 bnb", "0.5 bnb",
    "presale", "private sale", "buy presale", "fairlaunch", "public sale",
    # Meme Coin & Gambling Spams
    "pump.fun", "solana meme", "dexscreener.com/solana", "shitcoin",
    "casino", "slot", "judol", "gacor", "togel", "binance future signal", "vip signal"
]

# Detection Confidence Threshold (0 - 100)
AGENTIC_SCORE_THRESHOLD = int(os.getenv("AGENTIC_SCORE_THRESHOLD", "60"))

# Max Gas Fee Allowed per Tx in BNB (0.0004 BNB ~= $0.30 USD)
MAX_GAS_FEE_LIMIT_BNB = float(os.getenv("MAX_GAS_FEE_LIMIT_BNB", "0.0004"))

# Multi-wallet CLI runners
WALLETS = {
    1: {
        "name": os.getenv("WALLET_1_NAME", "Account 1"),
        "cmd": os.getenv("WALLET_1_CMD", "baw1"),
        "address": os.getenv("WALLET_1_ADDRESS", "0x5e3f75F6C6f877A712a011027910aE1AD46Af462")
    },
    2: {
        "name": os.getenv("WALLET_2_NAME", "Account 2"),
        "cmd": os.getenv("WALLET_2_CMD", "baw2"),
        "address": os.getenv("WALLET_2_ADDRESS", "0x4183c1E2dC29B931d7b2214b8d66F572E4a7F8bD")
    },
    3: {
        "name": os.getenv("WALLET_3_NAME", "Account 3"),
        "cmd": os.getenv("WALLET_3_CMD", "baw3"),
        "address": os.getenv("WALLET_3_ADDRESS", "0xD4ffBC4cc276BC60302E90DBd3D079e90e72861E")
    }
}
