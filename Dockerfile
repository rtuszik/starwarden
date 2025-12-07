FROM ghcr.io/astral-sh/uv:0.8-alpine

ENV PYTHONUNBUFFERED=1 \
    GITHUB_TOKEN="" \
    GITHUB_USERNAME="" \
    LINKWARDEN_URL="" \
    LINKWARDEN_TOKEN="" \
    COLLECTION_ID="" \
    CRON_SCHEDULE="0 6 * * *" \
    DOCKERIZED=true \
    OPT_TAG=true \
    OPT_TAG_GITHUB=true \
    OPT_TAG_GITHUBSTARS=true \
    OPT_TAG_LANGUAGE=false \
    OPT_TAG_USERNAME=false \
    OPT_TAG_CUSTOM=false

WORKDIR /app

COPY . /app
COPY docker/cron_job.sh docker/entrypoint.sh /app/

RUN uv sync --locked && \
    touch /app/starwarden.log && \
    chmod +x /app/cron_job.sh /app/entrypoint.sh && \
    mkdir -p /etc/crontabs

CMD ["/app/entrypoint.sh"]
