import os
import sys
import json
import subprocess
import time
from config import WALLETS

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

NATIVE_BNB = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

class AutoSeller:
    def __init__(self, min_usd_to_sell: float = 0.20):
        self.wallets = WALLETS
        self.min_usd_to_sell = min_usd_to_sell

    def get_wallet_balances(self, acc_id: int) -> list:
        """Query token balances in wallet using baw balance --json"""
        cmd_name = self.wallets[acc_id]["cmd"]
        try:
            res = subprocess.run(f"{cmd_name} wallet balance --json", shell=True, capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return data.get("data", [])
        except Exception as e:
            print(f"Error query balance on {cmd_name}: {e}")
        return []

    def check_swap_quote(self, acc_id: int, token_addr: str, qty: str) -> dict:
        """Cek apakah token memiliki likuiditas di DEX via baw market-order quote"""
        cmd_name = self.wallets[acc_id]["cmd"]
        cmd = f"{cmd_name} market-order quote --binanceChainId 56 --fromToken {token_addr} --toToken {NATIVE_BNB} --fromTokenQty {qty} --json"
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return data.get("data", {})
        except Exception:
            pass
        return {}

    def swap_to_bnb(self, acc_id: int, token_addr: str, qty: str) -> bool:
        """Swap token secara instan ke BNB via Market Order"""
        cmd_name = self.wallets[acc_id]["cmd"]
        cmd = f"{cmd_name} market-order swap --binanceChainId 56 --fromToken {token_addr} --toToken {NATIVE_BNB} --fromTokenQty {qty} --slippage auto --json"
        print(f"   ⚡ Menjalankan auto-swap ke BNB via {cmd_name}...")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                print(f"   ✅ Auto-swap Sukses! Token dikonversi menjadi BNB.")
                return True
            else:
                print(f"   ❌ Swap gagal: {res.stderr or res.stdout}")
        except Exception as e:
            print(f"   ❌ Swap error: {e}")
        return False

    def scan_and_liquidate(self, dry_run: bool = False):
        """Scan semua 3 akun, temukan token baru dan jual instan ke BNB sesuai harga pasar"""
        print("==================================================================")
        print("🧹 AUTO-SELLER & PORTFOLIO CLEANER (3 WALLETS)")
        print("==================================================================")
        print(f"⚙️ Mode: {'SIMULASI (Cek Harga Saja)' if dry_run else 'AUTO-LIQUIDATE (Langsung Jual ke BNB)'}")
        print(f"💵 Minimal Nilai Jual: ${self.min_usd_to_sell:.2f}")
        print("==================================================================")

        total_converted = 0
        for acc_id, w in self.wallets.items():
            print(f"\n🔍 Memeriksa portofolio [{w['name']}]...")
            tokens = self.get_wallet_balances(acc_id)
            if not tokens:
                print("   Tidak ada token terdeteksi atau query gagal.")
                continue

            for t in tokens:
                addr = t.get("address", "").lower()
                symbol = t.get("symbol") or t.get("token") or "UNKNOWN"
                bal_str = str(t.get("balance", "0"))
                val_str = str(t.get("value", "$0")).replace("$", "").replace(",", "")
                try:
                    usd_val = float(val_str)
                except ValueError:
                    usd_val = 0.0

                # Abaikan native BNB (jangan dijual)
                if addr == NATIVE_BNB.lower() or symbol == "BNB":
                    print(f"   💰 Native Gas: {bal_str[:8]} BNB (${usd_val:.2f}) [DIPERTAHANKAN]")
                    continue

                print(f"\n   📦 Ditemukan Token Airdrop: {symbol} ({bal_str}) - Nilai: ${usd_val:.2f}")
                print(f"      Address: {addr}")

                # Cek kuotasi harga pasar DEX
                quote = self.check_swap_quote(acc_id, addr, bal_str)
                if quote and quote.get("toTokenQty"):
                    expected_bnb = quote.get("toTokenQty")
                    print(f"      📈 Likuiditas DEX Tersedia! Estimasi hasil swap: ~{expected_bnb} BNB")
                    
                    if not dry_run:
                        if usd_val >= self.min_usd_to_sell or float(expected_bnb) > 0.0001:
                            success = self.swap_to_bnb(acc_id, addr, bal_str)
                            if success:
                                total_converted += 1
                        else:
                            print(f"      ⏳ Nilai terlalu kecil (< ${self.min_usd_to_sell}), ditahan sementara.")
                    else:
                        print(f"      [SIMULASI] Siap dijual langsung ke BNB di harga pasar.")
                else:
                    print(f"      ⚠️ Belum ada pair DEX / likuiditas belum open di PancakeSwap. Tersimpan aman.")

        print("\n==================================================================")
        print(f"🏁 Proses Selesai. Total Token Terkonversi ke BNB: {total_converted}")
        print("==================================================================\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auto Seller & Portfolio Cleaner")
    parser.add_argument("--dry-run", action="store_true", help="Cek likuiditas dan nilai token tanpa menjual")
    parser.add_argument("--sell", action="store_true", help="Langsung jual semua token airdrop ke BNB di harga market")
    args = parser.parse_args()

    seller = AutoSeller()
    seller.scan_and_liquidate(dry_run=not args.sell)
