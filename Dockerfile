FROM ghcr.io/astral-sh/uv:0.9.26-trixie-slim


ENV PYTHONUNBUFFERED=1
ENV GITHUB_TOKEN=""
ENV GITHUB_USERNAME=""
ENV LINKWARDEN_URL=""
ENV LINKWARDEN_TOKEN=""
ENV COLLECTION_ID=""
ENV CRON_SCHEDULE="0 6 * * *"
ENV DOCKERIZED=true

ENV OPT_TAG=true
ENV OPT_TAG_GITHUB=true
ENV OPT_TAG_GITHUBSTARS=true
ENV OPT_TAG_LANGUAGE=false
ENV OPT_TAG_USERNAME=false
ENV OPT_TAG_CUSTOM=false
ENV OPT_DELETE_DUPLICATE=false
ENV DEBUG=false

WORKDIR /app

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

COPY . .

RUN /usr/local/bin/uv sync --locked

# Create a cron job file
RUN echo '#!/bin/sh' > /app/cron_job.sh && \
    echo 'set -a' >> /app/cron_job.sh && \
    echo '. /app/.env' >> /app/cron_job.sh && \
    echo 'set +a' >> /app/cron_job.sh && \
    echo 'if [ -n "$COLLECTION_ID" ]; then' >> /app/cron_job.sh && \
    echo '     /app/.venv/bin/python -m starwarden.main -id "$COLLECTION_ID" >> /app/starwarden.log 2>&1' >> /app/cron_job.sh && \
    echo 'else' >> /app/cron_job.sh && \
    echo '    echo "Error: COLLECTION_ID is not set" >> /app/starwarden.log' >> /app/cron_job.sh && \
    echo 'fi' >> /app/cron_job.sh && \
    chmod +x /app/cron_job.sh


# Create the log file to be able to run tail
RUN touch /app/starwarden.log

# Create start script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'env | grep -v "PATH\|HOSTNAME\|HOME" > /app/.env' >> /app/start.sh && \
    echo 'echo "$CRON_SCHEDULE root /app/cron_job.sh" > /etc/cron.d/starwarden-cron' >> /app/start.sh && \
    echo 'chmod 0644 /etc/cron.d/starwarden-cron' >> /app/start.sh && \
    echo 'crontab /etc/cron.d/starwarden-cron' >> /app/start.sh && \
    echo 'cron' >> /app/start.sh && \
    echo 'if [ -n "$COLLECTION_ID" ]; then' >> /app/start.sh && \
    echo '    /app/.venv/bin/python -m starwarden.main -id "$COLLECTION_ID"' >> /app/start.sh && \
    echo 'else' >> /app/start.sh && \
    echo '    echo "Error: COLLECTION_ID is not set"' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo 'tail -f /app/starwarden.log' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/bin/sh", "-c", "/app/start.sh"]
