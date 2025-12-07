#!/bin/sh
# Export only the necessary environment variables to a file for cron
# Use proper format and escape special characters
{
    echo "GITHUB_TOKEN=\"$GITHUB_TOKEN\""
    echo "GITHUB_USERNAME=\"$GITHUB_USERNAME\""
    echo "LINKWARDEN_URL=\"$LINKWARDEN_URL\""
    echo "LINKWARDEN_TOKEN=\"$LINKWARDEN_TOKEN\""
    echo "COLLECTION_ID=\"$COLLECTION_ID\""
    echo "APPRISE_URLS=\"$APPRISE_URLS\""
    echo "OPT_TAG=\"$OPT_TAG\""
    echo "OPT_TAG_GITHUB=\"$OPT_TAG_GITHUB\""
    echo "OPT_TAG_GITHUBSTARS=\"$OPT_TAG_GITHUBSTARS\""
    echo "OPT_TAG_LANGUAGE=\"$OPT_TAG_LANGUAGE\""
    echo "OPT_TAG_USERNAME=\"$OPT_TAG_USERNAME\""
    echo "OPT_TAG_CUSTOM=\"$OPT_TAG_CUSTOM\""
    [ -n "$ENABLE_CONSOLE_LOGGING" ] && echo "ENABLE_CONSOLE_LOGGING=\"$ENABLE_CONSOLE_LOGGING\""
    [ -n "$CONSOLE_LEVEL" ] && echo "CONSOLE_LEVEL=\"$CONSOLE_LEVEL\""
} > /app/.env

# Setup cron job for root user
echo "$CRON_SCHEDULE /app/cron_job.sh >> /app/starwarden.log 2>&1" > /etc/crontabs/root

# Start busybox cron daemon
crond -f -l 2 &

# Run initial execution if COLLECTION_ID is set
if [ -n "$COLLECTION_ID" ]; then
    uv run /app/starwarden.py -id "$COLLECTION_ID"
else
    echo "Error: COLLECTION_ID is not set"
fi

# Keep container running and show logs
exec tail -f /app/starwarden.log
