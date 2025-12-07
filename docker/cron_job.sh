#!/bin/sh

set -a
. /app/.env
set +a
if [ -n "$COLLECTION_ID" ]; then
    uv run /app/starwarden.py -id "$COLLECTION_ID" >> /app/starwarden.log 2>&1
else
    echo "Error: COLLECTION_ID is not set" >> /app/starwarden.log
fi
