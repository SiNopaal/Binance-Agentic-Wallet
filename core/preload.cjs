/**
 * Binance Agentic Wallet (BAW) Multi-Account Preload Script
 * 
 * Functions:
 * 1. Bypasses ISP DNS hijacking for Binance CloudFront domains.
 * 2. Spoofs/sets custom device hostname per profile.
 * 3. Pins BINANCE_INSTANCE_ID to prevent session wipeouts caused by
 *    network interface MAC address drift (e.g. when connecting VPN/WARP/Hotspot).
 */

const os = require('os');
const dns = require('dns');

// 1. Pin Instance ID to prevent MAC drift session reset
// If process.env.BINANCE_INSTANCE_ID is not provided, use an environment-specific or hardware fallback
if (!process.env.BINANCE_INSTANCE_ID) {
  process.env.BINANCE_INSTANCE_ID = 'BAW-MASTER-NODE-PERM-ID';
}

// 2. Override os.hostname if custom device name is defined
if (process.env.BINANCE_DEVICE_NAME) {
  const custom = process.env.BINANCE_DEVICE_NAME;
  os.hostname = () => custom;
}

// 3. Bypass ISP DNS hijacking for Binance endpoints
const origLookup = dns.lookup;
const BINANCE_IPS = [
  '65.8.76.122',
  '65.8.76.127',
  '65.8.76.96',
  '65.8.76.116',
  '13.33.88.105'
];
let binanceIpIdx = 0;

dns.lookup = function(hostname, options, callback) {
  if (typeof options === 'function') {
    callback = options;
    options = {};
  }
  if (hostname === 'www.binance.com' || hostname === 'binance.com') {
    const ip = BINANCE_IPS[binanceIpIdx % BINANCE_IPS.length];
    binanceIpIdx++;
    if (options && options.all) {
      return callback(null, [{ address: ip, family: 4 }]);
    }
    return callback(null, ip, 4);
  }
  return origLookup.call(dns, hostname, options, callback);
};
