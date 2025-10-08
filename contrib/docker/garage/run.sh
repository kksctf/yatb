#!/usr/bin/env bash
set -euom pipefail

export RUST_LOG=garage=warn

KEY_NAME="yatb"
NODE_SIZE="32GB"

SHARED_DIR=/garage_shared
INIT_FLAG="$SHARED_DIR/.cluster-init"
KEY_FLAG="$SHARED_DIR/.key-init"

log() {
    echo "[=garage-init]" $@
}

log "Starting Garage server in bg"
/garage server &

GARAGE_PID=$!
sleep 1

NODE_ID=$(/garage status | grep -oP '^\w{16}' | head -1)

if [ ! -f "$INIT_FLAG" ]; then
    log "Initializing cluster layout..."
    /garage layout assign -z dc1 "$NODE_ID" -c "$NODE_SIZE"
    /garage layout apply --version 1
    # wait a second for garage to init
    sleep 1
    touch "$INIT_FLAG"
else
    log "Cluster layout already initialized, skipping..."
fi

if [ ! -f "$KEY_FLAG" ]; then
    log "Creating API key.."
    /garage key create "$KEY_NAME"
    touch "$KEY_FLAG"
else
    log "API key already exists."
fi

log "Force allow create buckets"
/garage key allow --create-bucket "$KEY_NAME"

ACCESS_KEY=$(/garage key info "$KEY_NAME" | grep 'Key ID:' | awk '{print $3}')
SECRET_KEY=$(/garage key info --show-secret "$KEY_NAME" | grep 'Secret key:' | awk '{print $3}')

echo "$ACCESS_KEY" > "$SHARED_DIR/access_key"
echo "$SECRET_KEY" > "$SHARED_DIR/secret_key"

# kill init garage instance
kill $GARAGE_PID

log "Starting real garage"
# drop-exec to real garage (don't leave bash behind!)
exec /garage server
