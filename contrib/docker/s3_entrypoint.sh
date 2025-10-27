#!/usr/bin/env bash

SHARED_DIR=/garage_shared

export S3_HOST="garage"
export S3_PORT="3900"
export S3_HTTPS="0"

export S3_ACCESS=`cat "$SHARED_DIR/access_key"`
export S3_SECRET=`cat "$SHARED_DIR/secret_key"`

export S3_REGION="garage"

exec /app/.venv/bin/python3 -m gunicorn s3_srv.app:app \
    --worker-class=uvicorn.workers.UvicornWorker \
    --workers=2 \
    --log-level=warning \
    --bind=0.0.0.0:80 \
    --forwarded-allow-ips=*
