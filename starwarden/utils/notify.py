import apprise

from starwarden.utils.logger import get_logger

logger = get_logger()


def send_notification(config: dict, message: str, title: str = "Starwarden Notification"):
    apprise_urls = config.get("APPRISE_URLS")
    if not apprise_urls:
        logger.info("No APPRISE_URLS set, skipping notification.")
        return

    apobj = apprise.Apprise()

    for url in apprise_urls.split(","):
        if url.strip():
            apobj.add(url.strip())

    if len(apobj) == 0:
        logger.warning("No valid Apprise URLs were found after processing the APPRISE_URLS variable.")
        return

    if not apobj.notify(body=message, title=title):
        logger.error("Failed to send notification to one or more Apprise targets.")
    else:
        logger.info("Successfully sent notification.")
