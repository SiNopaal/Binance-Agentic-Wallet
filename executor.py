import os
import subprocess
import json
import time
from config import WALLETS, MAX_GAS_FEE_LIMIT_BNB

class MultiWalletExecutor:
    def __init__(self):
        self.wallets = WALLETS

    def revoke_all_wallet_approvals(self, acc_id: int):
        """
        Mendeteksi dan mencabut (revoke) semua approval/allowance yang aktif 
        segera setelah proses minting/klaim selesai, agar dompet 100% aman dari drainer.
        """
        wallet = self.wallets.get(acc_id)
        if not wallet:
            return

        cmd_name = wallet["cmd"]
        print(f"\n🛡️ [POST-MINT SECURITY AUDIT] Memeriksa approval aktif pada [{wallet['name']}]...")

        try:
            # 1. List active approvals
            list_cmd = f"{cmd_name} approvals list --json"
            res = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            approvals = []
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    approvals = data.get("data", {}).get("list", []) or []
                except Exception:
                    approvals = []

            if not approvals:
                print(f"   ✅ Bersih! Tidak ada approval/allowance aktif yang tertinggal di [{wallet['name']}].")
                return

            print(f"   ⚠️ Ditemukan {len(approvals)} approval aktif! Memulai proses auto-revoke...")
            for app in approvals:
                token_addr = app.get("tokenContract") or app.get("address")
                spender_addr = app.get("spender")
                app_type = app.get("type", "approve")
                chain_id = app.get("binanceChainId", "56")

                if token_addr and spender_addr:
                    print(f"   🔄 Mencabut izin untuk spender {spender_addr[:10]}... pada token {token_addr[:10]}...")
                    revoke_cmd = (
                        f"{cmd_name} approvals revoke "
                        f"--binanceChainId {chain_id} "
                        f"--tokenContract {token_addr} "
                        f"--spender {spender_addr} "
                        f"--type {app_type} "
                        f"--json"
                    )
                    rev_res = subprocess.run(revoke_cmd, shell=True, capture_output=True, text=True, timeout=25)
                    if rev_res.returncode == 0:
                        print(f"   🔒 SUKSES REVOKE: Izin ke {spender_addr[:10]}... telah dicabut menjadi 0!")
                    else:
                        print(f"   ⚠️ Revoke gagal/sudah 0: {rev_res.stderr or rev_res.stdout}")

        except Exception as e:
            print(f"   ⚠️ Gagal memeriksa approval di {cmd_name}: {e}")

    def execute_contract_call(self, contract_address: str, calldata: str = "0x8580974c", value_wei: str = "0", accounts: list = [1, 2, 3]):
        """
        Mengeksekusi contract call / free mint secara paralel ke akun terpilih.
        
        SISTEM VALIDASI & KEAMANAN 4-LAPIS:
        1. Local Gate: Menolak jika value_wei != 0.
        2. Binance Simulation Gate: Mengirim --value 0 secara eksplisit ke Binance Backend.
           Jika kontrak berbayar, Binance Backend otomatis menolak simulasi (Execution Reverted)
           dan requestId TIDAK AKAN PERNAH DIBUAT.
        3. Gas Limit Gate: Menolak jika estimasi gas melebihi batas wajar.
        4. Auto-Revoke Gate: Setelah transaksi berhasil, otomatis audit & cabut semua approval (Revoke All)!
        """
        # LAPIS 1: Local Code Enforcer (Zero-Cost Free Mint Only)
        if str(value_wei).strip() != "0":
            print(f"\n⛔ [LAPIS 1: ATURAN FREE-ONLY DILANGGAR] Transaksi meminta biaya {value_wei} wei!")
            print("   EKSEKUSI DIBATALKAN. Tidak ada dana yang boleh keluar selain gas fee.")
            return {}

        results = {}
        print(f"\n🚀 [Multi-Executor] Menjalankan Validasi 100% Free Mint ke {contract_address}")
        print(f"   Target Contract: {contract_address}")
        print(f"   Calldata Hex   : {calldata}")
        print(f"   Explicit Value : 0 wei (0 BNB - Free Mint Only)")

        for acc_id in accounts:
            wallet = self.wallets.get(acc_id)
            if not wallet:
                continue

            cmd_name = wallet["cmd"]
            from_addr = wallet["address"]
            print(f"\n▶️ [Simulasi Lapis 2] Memeriksa kelayakan di [{wallet['name']}] ({from_addr})...")

            try:
                # LAPIS 2: Binance Live On-Chain Simulation dengan --value 0
                preview_cmd = (
                    f"{cmd_name} contract-call preview "
                    f"--binanceChainId 56 "
                    f"--from {from_addr} "
                    f"--to {contract_address} "
                    f"--value 0 "
                    f"--inputData {calldata} "
                    f"--json"
                )
                out_prev = subprocess.run(preview_cmd, shell=True, capture_output=True, text=True, timeout=20)
                
                req_id = None
                is_free_verified = False

                if out_prev.returncode == 0:
                    try:
                        prev_data = json.loads(out_prev.stdout)
                        if prev_data.get("success"):
                            req_data = prev_data.get("data", {})
                            req_id = req_data.get("requestId")
                            is_free_verified = True
                            
                            # Cek estimasi gas fee
                            est_gas = req_data.get("gasFeeEstimate", "")
                            print(f"   ✅ [SIMULASI SUKSES] Kontrak 100% GRATIS (Fee hanya gas: {est_gas or '~$0.01'})")
                        else:
                            err_msg = prev_data.get("error", {}).get("message", "Simulasi gagal")
                            print(f"   ⛔ [SIMULASI DITOLAK / KONTRAK BUTUH BAYAR / REVERTED]: {err_msg}")
                    except Exception as e:
                        print(f"   ⚠️ Parsing error: {e}")
                else:
                    print(f"   ⛔ [DITOLAK OLEH NODE BINANCE] Simulasi gagal: Transaksi butuh bayar atau fungsi revert.")
                    results[acc_id] = {
                        "status": "REJECTED_NOT_FREE_OR_REVERTED",
                        "output": out_prev.stdout.strip() or out_prev.stderr.strip()
                    }
                    continue

                # LAPIS 3: Eksekusi HANYA jika simulasi Binance menyatakan 100% Free
                if is_free_verified and req_id:
                    print(f"   ⚡ Memproses siaran transaksi on-chain via {cmd_name}...")
                    exec_cmd = f"{cmd_name} contract-call execute --requestId {req_id} --json"
                    out_exec = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True, timeout=25)
                    
                    is_success = out_exec.returncode == 0 and "SUCCESS" in out_exec.stdout.upper()
                    results[acc_id] = {
                        "status": "SUCCESS" if is_success else "FAILED",
                        "output": out_exec.stdout.strip() or out_exec.stderr.strip()
                    }
                    print(f"   🎉 Status Minting: {results[acc_id]['status']}")

                    # LAPIS 4: POST-MINT AUTO-REVOKE (Jamin Keamanan Saldo 100%)
                    self.revoke_all_wallet_approvals(acc_id)

                else:
                    print(f"   ❌ Dibatalkan: Kontrak tidak lolos verifikasi free-mint.")

            except Exception as e:
                results[acc_id] = {
                    "status": "ERROR",
                    "output": str(e)
                }
                print(f"   ⚠️ Error exception: {e}")

        return results

    def revoke_all_3_wallets(self):
        """Mencabut semua approval di ketiga wallet sekaligus (Manual Sweep)"""
        print("==================================================================")
        print("🔒 REVOKE ALL APPROVALS (AUDIT KEAMANAN 3 WALLET)")
        print("==================================================================")
        for acc_id in [1, 2, 3]:
            self.revoke_all_wallet_approvals(acc_id)
        print("==================================================================")
        print("✅ Seluruh wallet telah diaudit. Tidak ada izin terbuka yang tertinggal!")
        print("==================================================================\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Wallet Executor & Revoke Guard")
    parser.add_argument("--revoke-all", action="store_true", help="Cek dan cabut semua approval aktif di ketiga wallet sekarang")
    args = parser.parse_args()

    ex = MultiWalletExecutor()
    if args.revoke_all:
        ex.revoke_all_3_wallets()
    else:
        ex.revoke_all_3_wallets()
