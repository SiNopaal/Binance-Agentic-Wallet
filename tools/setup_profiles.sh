#!/usr/bin/env bash
# Profile shortcut generator for Linux/macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PRELOAD_FILE="$ROOT_DIR/core/preload.cjs"

read -p "Enter total number of accounts to generate (default 5): " NUM_ACCOUNTS
NUM_ACCOUNTS=${NUM_ACCOUNTS:-5}

TARGET_BIN="$HOME/.local/bin"
mkdir -p "$TARGET_BIN"

echo "[*] Generating baw1 through baw$NUM_ACCOUNTS in $TARGET_BIN..."

for i in $(seq 1 "$NUM_ACCOUNTS"); do
    CMD_FILE="$TARGET_BIN/baw$i"
    cat <<EOF > "$CMD_FILE"
#!/usr/bin/env bash
export BINANCE_BAW_DIR="\$HOME/.baw/profiles/acc$i"
export BINANCE_KEYTAR_SERVICE="baw_acc$i"
export BINANCE_DEVICE_NAME="Agent-Node-Acc$i"
export NODE_OPTIONS="--require $PRELOAD_FILE"
exec baw "\$@"
EOF
    chmod +x "$CMD_FILE"
    echo "  [+] Created: $CMD_FILE"
done

echo
echo "SUCCESS! Ensure $TARGET_BIN is in your PATH."
echo "You can now run: baw1 wallet status"
