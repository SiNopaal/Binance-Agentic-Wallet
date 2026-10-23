const os = require('os');

// Override os.hostname if custom device name is defined
if (process.env.BINANCE_DEVICE_NAME) {
  const custom = process.env.BINANCE_DEVICE_NAME;
  os.hostname = () => custom;
}
