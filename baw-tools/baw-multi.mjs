import { spawn, execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';

const BAW_HOME = process.env.BAW_HOME || path.join(os.homedir(), '.baw');
const PROFILES_DIR = path.join(BAW_HOME, 'profiles');
const PRELOAD_SCRIPT = path.join(BAW_HOME, 'preload.cjs');

const accounts = {
  1: { id: 1, name: 'Account 1', dir: path.join(PROFILES_DIR, 'acc1'), service: 'baw_acc1', device: 'Agent-Node-Acc1' },
  2: { id: 2, name: 'Account 2', dir: path.join(PROFILES_DIR, 'acc2'), service: 'baw_acc2', device: 'Agent-Node-Acc2' },
  3: { id: 3, name: 'Account 3', dir: path.join(PROFILES_DIR, 'acc3'), service: 'baw_acc3', device: 'Agent-Node-Acc3' }
};

// Ensure directories exist
for (const acc of Object.values(accounts)) {
  if (!fs.existsSync(acc.dir)) {
    fs.mkdirSync(acc.dir, { recursive: true });
  }
}

function getAccountEnv(accId) {
  const acc = accounts[accId];
  const env = {
    ...process.env,
    BINANCE_BAW_DIR: acc.dir,
    BINANCE_KEYTAR_SERVICE: acc.service,
    BINANCE_DEVICE_NAME: acc.device
  };
  if (fs.existsSync(PRELOAD_SCRIPT)) {
    env.NODE_OPTIONS = `--require "${PRELOAD_SCRIPT}"`;
  }
  return env;
}

function appendActivityLog(accId, cmdText, resultText) {
  try {
    const acc = accounts[accId];
    const logFile = path.join(acc.dir, 'activity.log');
    const timestamp = new Date().toISOString();
    const entry = `[${timestamp}] [CMD: ${cmdText}]\n${resultText.trim()}\n----------------------------------------------------\n`;
    fs.appendFileSync(logFile, entry, 'utf8');
  } catch (err) {
    // Ignore logging errors
  }
}

function runBawSync(accId, args) {
  try {
    const out = execSync(`baw ${args}`, {
      env: getAccountEnv(accId),
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe']
    });
    appendActivityLog(accId, `baw ${args}`, out);
    return out;
  } catch (err) {
    const errOut = err.stdout || err.stderr || err.message;
    appendActivityLog(accId, `baw ${args} (ERROR)`, errOut);
    return errOut;
  }
}

async function showAllStatus() {
  console.log('================================================================');
  console.log('🤖 BINANCE AGENTIC WALLET (BAW) - MULTI-ACCOUNT STATUS AUDIT');
  console.log('================================================================');

  for (const [id, acc] of Object.entries(accounts)) {
    console.log(`\n📌 [${acc.name}] (Profile: ${acc.service} | Device: ${acc.device})`);
    try {
      const statusOut = execSync('baw status --json', {
        env: getAccountEnv(id),
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe']
      });
      const data = JSON.parse(statusOut);
      const isAuth = data.data?.authenticated;
      const addr = data.data?.address || 'Belum Terhubung';
      const bscChain = data.data?.chains?.find(c => c.name === 'BSC');
      const bnbBal = bscChain?.balance || '0';

      console.log(`   • Status Sesi: ${isAuth ? '🟢 LOGIN AKTIF' : '🔴 BELUM LOGIN'}`);
      console.log(`   • Address    : ${addr}`);
      console.log(`   • Saldo Gas  : ${bnbBal} BNB`);
    } catch (e) {
      console.log(`   ❌ Gagal membaca status: ${e.message}`);
    }
  }
  console.log('\n================================================================');
}

function spawnInteractiveBaw(accId, args) {
  const acc = accounts[accId];
  if (!acc) {
    console.error(`Akun ID ${accId} tidak valid. Gunakan 1, 2, atau 3.`);
    process.exit(1);
  }

  console.log(`🚀 Menjalankan perintah BAW untuk [${acc.name}]...`);
  console.log(`   Service: ${acc.service} | Device: ${acc.device}\n`);

  const child = spawn('cmd.exe', ['/c', 'baw', ...args], {
    env: getAccountEnv(accId),
    stdio: 'inherit'
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

const args = process.argv.slice(2);
const command = args[0];

if (!command || command === 'status') {
  showAllStatus();
} else if (['1', '2', '3'].includes(command)) {
  const accId = parseInt(command, 10);
  const bawArgs = args.slice(1);
  spawnInteractiveBaw(accId, bawArgs);
} else {
  console.log(`
Penggunaan Binance Agentic Wallet Multi-Profile Manager:
  node baw-multi.mjs status               - Cek status & saldo semua dompet
  node baw-multi.mjs <1|2|3> <command>    - Jalankan perintah baw untuk dompet tertentu

Contoh:
  node baw-multi.mjs 1 login              - Login Akun 1 via QR Code
  node baw-multi.mjs 2 wallet balance     - Cek saldo Akun 2
  node baw-multi.mjs 3 approvals list     - Cek active approvals Akun 3
`);
}
