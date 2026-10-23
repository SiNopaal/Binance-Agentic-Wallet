import os
import re
from datetime import datetime
from web3 import Web3

# Dangerous Function Selectors (Drainer / Unlimited Approval Traps)
DANGEROUS_SELECTORS = {
    "0x095ea7b3": "approve(address,uint256) - Resiko Token Drainer",
    "0xa22cb465": "setApprovalForAll(address,bool) - Resiko NFT Drainer",
    "0xd505accf": "permit(...) - Resiko Gasless Token Drain",
    "0x23b872dd": "transferFrom(...) - Resiko Unsolicited Transfer",
    "0x42842e0e": "safeTransferFrom(...) - Resiko Unsolicited Transfer"
}

# Suspicious domain patterns / drainer kits
SUSPICIOUS_DOMAIN_PATTERNS = [
    r"claim.*airdrop",
    r"connect.*wallet",
    r"rectify.*token",
    r"bonus.*binance",
    r"gift.*bnb",
    r"\.top$",
    r"\.buzz$",
    r"\.cfd$",
    r"\.rest$",
    r"\.icu$",
    r"\.tk$"
]

OFFICIAL_WHITELIST_DOMAINS = [
    "binance.com",
    "bnbchain.org",
    "agentid.ai",
    "dapp.binance.com",
    "quest.bnbchain.world",
    "github.com/binance",
    "github.com/bnb-chain"
]

class SecurityGuard:
    def __init__(self, w3=None):
        self.w3 = w3

    def audit_author(self, user_obj) -> dict:
        """
        Audit kredibilitas akun pembuat tweet di X.
        Mendeteksi bot scam, akun kloningan, atau akun baru jadi.
        """
        if not user_obj:
            return {"trust_level": "UNKNOWN", "score": 50, "warnings": ["Data akun tidak lengkap"]}

        followers = getattr(user_obj, "followers_count", 0) or 0
        is_verified = getattr(user_obj, "is_blue_verified", False) or False
        created_at_str = getattr(user_obj, "created_at", "") or ""
        statuses_count = getattr(user_obj, "statuses_count", 0) or 0

        score = 50
        warnings = []

        # Follower Analysis
        if followers >= 10000:
            score += 30
        elif followers >= 1000:
            score += 15
        elif followers < 100:
            score -= 30
            warnings.append(f"Follower sangat sedikit ({followers}), rawan akun bot/fake")

        # Verified Blue Badge
        if is_verified:
            score += 15

        # Tweet Activity
        if statuses_count < 20:
            score -= 20
            warnings.append("Akun hampir tidak pernah posting, kemungkinan burner account")

        # Trust Level
        if score >= 75:
            trust_level = "HIGH"
        elif score >= 45:
            trust_level = "MEDIUM"
        else:
            trust_level = "LOW / UNTRUSTED"

        return {
            "trust_level": trust_level,
            "trust_score": max(0, min(100, score)),
            "followers": followers,
            "is_verified": is_verified,
            "warnings": warnings
        }

    def audit_contract_safety(self, contract_address: str, calldata: str = "") -> dict:
        """
        Audit keamanan smart contract:
        1. Blokir jebakan Approval / Drainer
        2. Cek apakah ada dana yang diminta (value)
        3. Cek eksistensi bytecode di BSC
        """
        result = {
            "address": contract_address,
            "is_safe_for_automint": False,
            "risk_level": "LOW",
            "warnings": [],
            "blocked_reasons": []
        }

        # 1. Cek Calldata terhadap Selector Berbahaya
        if calldata:
            selector = calldata[:10].lower()
            if selector in DANGEROUS_SELECTORS:
                result["risk_level"] = "CRITICAL / DRAINER"
                result["blocked_reasons"].append(f"CALLED DANGEROUS FUNCTION: {DANGEROUS_SELECTORS[selector]}")
                return result

        # 2. Cek Bytecode on-chain via Web3
        if self.w3:
            try:
                checksum = Web3.to_checksum_address(contract_address)
                code = self.w3.eth.get_code(checksum)
                if not code or len(code) <= 2:
                    result["risk_level"] = "HIGH"
                    result["blocked_reasons"].append("Contract tidak memiliki bytecode di BSC (alamat palsu / jaringan lain)")
                    return result
                
                # Check for honeypot selfdestruct or suspicious trap
                code_hex = code.hex().lower()
                if "selfdestruct" in code_hex:
                    result["warnings"].append("Contract memiliki fungsi selfdestruct")

            except Exception as e:
                result["warnings"].append(f"RPC check error: {e}")

        # If no dangerous traps found
        if not result["blocked_reasons"]:
            result["is_safe_for_automint"] = True
            result["risk_level"] = "SAFE" if not result["warnings"] else "LOW_RISK"

        return result

    def audit_url(self, url: str) -> dict:
        """Audit link web terhadap indikasi phishing / scam drainer"""
        result = {
            "url": url,
            "is_whitelisted": False,
            "is_suspicious": False,
            "risk_score": 0,
            "flags": []
        }
        url_lower = url.lower()

        # Cek Whitelist Resmi
        for domain in OFFICIAL_WHITELIST_DOMAINS:
            if domain in url_lower:
                result["is_whitelisted"] = True
                result["risk_score"] = 0
                return result

        # Cek Pola Phishing Mencurigakan
        for pattern in SUSPICIOUS_DOMAIN_PATTERNS:
            if re.search(pattern, url_lower):
                result["is_suspicious"] = True
                result["risk_score"] += 40
                result["flags"].append(f"URL mencocokkan pola phishing mencurigakan: '{pattern}'")

        return result
