import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from web3 import Web3
from config import (
    BSC_RPC_LIST,
    AGENTIC_KEYWORDS,
    NEGATIVE_KEYWORDS,
    AGENTIC_SCORE_THRESHOLD,
    AGENTIC_REGISTRIES
)

# Connect Web3 to BSC
w3 = None
for rpc in BSC_RPC_LIST:
    try:
        provider = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 5}))
        if provider.is_connected():
            w3 = provider
            break
    except Exception:
        continue

# Common Agentic & Mint Function Selectors
MINT_SELECTORS = {
    "0x8580974c": "AI Token Mint (BNB Agent Studio)",
    "0x1249c58b": "mint()",
    "0xa0712d68": "mint(uint256)",
    "0x40c10f19": "mint(address,uint256)",
    "0x4e71d92d": "claim()",
    "0x379607f5": "claim(uint256)",
    "0x6a627842": "mint(address)",
    "0x2e1a7d4d": "withdraw(uint256)",
    "0x095ea7b3": "approve(address,uint256)"
}

class AgenticDetector:
    def __init__(self):
        self.w3 = w3

    def extract_contracts(self, text: str) -> list:
        """Ekstrak semua address contract EVM 0x 42-karakter"""
        pattern = r"\b(0x[a-fA-F0-9]{40})\b"
        matches = re.findall(pattern, text)
        # Deduplicate preserving order
        return list(dict.fromkeys([Web3.to_checksum_address(m) for m in matches]))

    def extract_urls(self, text: str) -> list:
        """Ekstrak semua URL yang valid"""
        pattern = r"https?://[^\s<>\"'()]+"
        matches = re.findall(pattern, text)
        # Filter out common telegram/t.me internal links if not relevant
        cleaned = []
        for u in matches:
            u_clean = u.rstrip(".,;!?:")
            if not u_clean.startswith("https://t.me/c/") and not u_clean.endswith(".jpg"):
                cleaned.append(u_clean)
        return list(dict.fromkeys(cleaned))

    def check_negative_filters(self, text: str) -> tuple[bool, str]:
        """Cek apakah mengandung kata kunci spam / koin micin / casino"""
        text_lower = text.lower()
        for neg in NEGATIVE_KEYWORDS:
            if neg in text_lower:
                return True, f"Negative keyword match: '{neg}'"
        return False, ""

    def inspect_contract_on_bsc(self, address: str) -> dict:
        """Periksa smart contract secara langsung di blockchain BSC"""
        result = {
            "address": address,
            "is_contract": False,
            "has_mint_func": False,
            "detected_selectors": [],
            "is_agentic_registry": False,
            "score_boost": 0
        }
        if not self.w3:
            return result

        try:
            checksum_addr = Web3.to_checksum_address(address)
            code = self.w3.eth.get_code(checksum_addr)
            if code and len(code) > 2:
                result["is_contract"] = True
                result["score_boost"] += 20
                code_hex = code.hex().lower()

                # Check if it's in known Agentic registries
                if checksum_addr.lower() in [r.lower() for r in AGENTIC_REGISTRIES]:
                    result["is_agentic_registry"] = True
                    result["score_boost"] += 50
                    result["detected_selectors"].append("Verified BNB Agent Studio Registry")

                # Check function selectors in bytecode
                for sel, desc in MINT_SELECTORS.items():
                    # Check selector hex without 0x
                    clean_sel = sel[2:].lower()
                    if clean_sel in code_hex:
                        result["has_mint_func"] = True
                        result["detected_selectors"].append(f"{sel} ({desc})")
                        result["score_boost"] += 25

                # Check for string hints inside bytecode
                if b"agent" in code or b"agentid" in code or b".ai" in code:
                    result["score_boost"] += 30
                    result["detected_selectors"].append("Bytecode contains 'agent/.ai' keyword")

        except Exception as e:
            result["error"] = str(e)

        return result

    async def inspect_url_metadata(self, url: str) -> dict:
        """Fetch URL web dApp dan analisa apakah menuntut Agentic / .ai / Binance Agentic Wallet"""
        result = {
            "url": url,
            "status_code": 0,
            "agentic_signals": [],
            "score_boost": 0
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    result["status_code"] = resp.status
                    if resp.status == 200:
                        html = await resp.text()
                        html_lower = html.lower()

                        # Check for High Agentic Signals
                        for kw in AGENTIC_KEYWORDS["high"]:
                            if kw in html_lower:
                                result["agentic_signals"].append(f"Web contains high-signal: '{kw}'")
                                result["score_boost"] += 35

                        # Check for Medium Agentic Signals
                        for kw in AGENTIC_KEYWORDS["medium"]:
                            if kw in html_lower:
                                result["agentic_signals"].append(f"Web contains signal: '{kw}'")
                                result["score_boost"] += 15

                        # Check for Web3 / Wallet Connector
                        if "binance" in html_lower or "bnbchain" in html_lower:
                            result["agentic_signals"].append("Web integrated with Binance/BNB Chain")
                            result["score_boost"] += 15

                        if ".ai" in html_lower and ("connect" in html_lower or "wallet" in html_lower or "mint" in html_lower):
                            result["agentic_signals"].append("Web requires .ai Agent ID connection")
                            result["score_boost"] += 30

        except Exception as e:
            result["error"] = str(e)

        return result

    async def analyze(self, text: str) -> dict:
        """
        Deep analysis pipeline:
        1. Negative spam check
        2. Text NLP scoring
        3. Contract on-chain inspection (BSC)
        4. dApp Web inspection
        5. Final confidence score & verdict
        """
        report = {
            "text_preview": text[:120].strip() + ("..." if len(text) > 120 else ""),
            "is_agentic": False,
            "confidence_score": 0,
            "reasons": [],
            "contracts": [],
            "urls": [],
            "action_type": "UNKNOWN"
        }

        # 1. Negative Filter
        is_neg, neg_reason = self.check_negative_filters(text)
        if is_neg:
            report["reasons"].append(f"REJECTED: {neg_reason}")
            return report

        score = 0
        text_lower = text.lower()

        # 2. Text Keyword Scoring
        for kw in AGENTIC_KEYWORDS["high"]:
            if kw in text_lower:
                score += 35
                report["reasons"].append(f"Found High Agentic Keyword in chat: '{kw}' (+35)")

        for kw in AGENTIC_KEYWORDS["medium"]:
            if kw in text_lower:
                score += 15
                report["reasons"].append(f"Found Medium Agentic Keyword in chat: '{kw}' (+15)")

        for kw in AGENTIC_KEYWORDS["action"]:
            if kw in text_lower:
                score += 10
                report["reasons"].append(f"Found Action Keyword in chat: '{kw}' (+10)")
                if report["action_type"] == "UNKNOWN":
                    report["action_type"] = kw.upper()

        # 3. Extract & Inspect Contracts
        contracts = self.extract_contracts(text)
        report["contracts"] = contracts
        for c in contracts:
            c_info = self.inspect_contract_on_bsc(c)
            if c_info["is_contract"]:
                score += c_info["score_boost"]
                report["reasons"].append(f"Contract {c} verified on BSC (+{c_info['score_boost']})")
                if c_info["detected_selectors"]:
                    report["reasons"].append(f"Selectors: {', '.join(c_info['detected_selectors'])}")
                    report["action_type"] = "MINT / CLAIM"

        # 4. Extract & Inspect URLs
        urls = self.extract_urls(text)
        report["urls"] = urls
        for u in urls[:2]: # Check at most 2 URLs
            u_info = await self.inspect_url_metadata(u)
            if u_info["score_boost"] > 0:
                score += u_info["score_boost"]
                report["reasons"].append(f"URL {u} inspected (+{u_info['score_boost']}): {', '.join(u_info['agentic_signals'])}")

        # 5. Calculate Final Score
        report["confidence_score"] = min(100, score)
        report["is_agentic"] = report["confidence_score"] >= AGENTIC_SCORE_THRESHOLD

        return report
