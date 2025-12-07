import argparse
import os
import sys

from dotenv import load_dotenv

from starwarden.utils.logger import get_logger

logger = get_logger()


def parse_args():
    parser = argparse.ArgumentParser(description="Export GitHub starred repositories as individual links to Linkwarden")
    parser.add_argument("-id", type=int, help="Specify the collection ID to sync")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def load_env():
    load_dotenv()
    config = {
        "github_token": os.getenv("GITHUB_TOKEN"),
        "github_username": os.getenv("GITHUB_USERNAME"),
        "linkwarden_url": os.getenv("LINKWARDEN_URL"),
        "linkwarden_token": os.getenv("LINKWARDEN_TOKEN"),
        "opt_tag": os.getenv("OPT_TAG", "false").lower() in ("true", "1"),
        "opt_tag_github": os.getenv("OPT_TAG_GITHUB", "false").lower() in ("true", "1"),
        "opt_tag_githubStars": os.getenv("OPT_TAG_GITHUBSTARS", "false").lower() in ("true", "1"),
        "opt_tag_language": os.getenv("OPT_TAG_LANGUAGE", "false").lower() in ("true", "1"),
        "opt_tag_username": os.getenv("OPT_TAG_USERNAME", "false").lower() in ("true", "1"),
        "opt_tag_custom": os.getenv("OPT_TAG_CUSTOM", ""),
        "APPRISE_URLS": os.getenv("APPRISE_URLS"),
        "DOCKERIZED": os.getenv("DOCKERIZED", "false").lower() in ("true", "1"),
    }

    if not all([config["github_username"], config["linkwarden_url"], config["linkwarden_token"]]):
        logger.error("Missing required environment variables. Please check your .env file.")
        sys.exit(1)

    return config
