import json
import logging
import os
import sys
import time
from argparse import ArgumentParser
from math import ceil

import requests
from dotenv import load_dotenv
from github import Github, GithubException, RateLimitExceededException
from urllib3 import Retry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main_menu():
    print("Choose an option:")
    print("1. Update existing GitHub Stars collection")
    print("2. Create a new GitHub Stars collection")
    while True:
        choice = input("Enter your choice (1 or 2): ")
        if choice in ["1", "2"]:
            return int(choice)
        print("Invalid choice. Please enter 1 or 2.")


def handle_rate_limit(e, retry_after=None):
    if retry_after is None:
        retry_after = e.headers.get("Retry-After", 60)

    retry_after = int(retry_after)
    logger.warning(
        f"Rate limit exceeded. Waiting for {retry_after} seconds before retrying."
    )
    time.sleep(retry_after)


def starred_repos(user):
    starred = user.get_starred()
    total_pages = ceil(starred.totalCount / 30)

    for page_num in range(0, total_pages):
        while True:
            try:
                for repo in starred.get_page(page_num):
                    yield repo
                break
            except RateLimitExceededException as e:
                handle_rate_limit(e)
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    handle_rate_limit(e)
                else:
                    logger.error(f"GitHub API error: {str(e)}")
                    raise


def config_retry(backoff_factor=1.0, total=8):
    Retry.DEFAULT_BACKOFF_MAX = backoff_factor * 2 ** (total - 1)
    return Retry(total=total, backoff_factor=backoff_factor)


def parse_args():
    parser = ArgumentParser(
        description="Export GitHub starred repositories as individual links to Linkwarden"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actually creating links",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def get_existing_links(linkwarden_url, linkwarden_token, collection_id):
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    existing_links = set()
    page = 1
    while True:
        response = requests.get(
            f"{linkwarden_url}/api/v1/links?collectionId={collection_id}&page={page}",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        links = data.get("response", [])
        if not links:
            break
        existing_links.update(link["url"] for link in links)
        page += 1
    return existing_links


def get_linkwarden_collections(linkwarden_url, linkwarden_token):
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(f"{linkwarden_url}/api/v1/collections", headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Raw API Response: {json.dumps(data, indent=2)}")
        collections = data.get("response", [])
        logger.debug(f"Parsed collections: {json.dumps(collections, indent=2)}")
        return collections
    except requests.RequestException as e:
        logger.error(f"Error fetching collections from Linkwarden: {str(e)}")
        return None


def create_linkwarden_collection(
    linkwarden_url, linkwarden_token, name, description=""
):
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    data = {"name": name}
    try:
        response = requests.post(
            f"{linkwarden_url}/api/v1/collections", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error creating new collection in Linkwarden: {str(e)}")
        return None


def select_or_create_collection(linkwarden_url, linkwarden_token, dry_run=False):
    collections = get_linkwarden_collections(linkwarden_url, linkwarden_token)
    if collections is None:
        logger.error(
            "Failed to fetch collections. Please check your Linkwarden connection."
        )
        return None

    logger.debug(f"Collections type: {type(collections)}")
    logger.debug(f"Collections content: {collections}")

    if not collections:
        logger.info("No collections found.")
    else:
        print("Available collections:")
        for i, collection in enumerate(collections, 1):
            logger.debug(f"Collection {i} type: {type(collection)}")
            logger.debug(f"Collection {i} content: {collection}")
            if isinstance(collection, dict):
                print(
                    f"{i}. {collection.get('name', 'Unnamed')} (ID: {collection.get('id', 'Unknown')}) - {collection.get('description', 'No description')}"
                )
            elif isinstance(collection, str):
                print(f"{i}. {collection}")
            else:
                print(f"{i}. Unknown collection type")

    print(f"{len(collections) + 1}. Create a new collection")

    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(collections):
                selected = collections[choice - 1]
                if isinstance(selected, dict):
                    return selected.get("id")
                else:
                    logger.error(
                        f"Selected collection is not in the expected format. Selected: {selected}"
                    )
                    return None
            elif choice == len(collections) + 1:
                name = input("Enter the name for the new collection: ")
                description = input(
                    "Enter a description for the new collection (optional): "
                )
                if dry_run:
                    logger.info(f"[DRY RUN] Would create new collection: {name}")
                    return "dry_run_collection_id"
                new_collection = create_linkwarden_collection(
                    linkwarden_url, linkwarden_token, name, description
                )
                if new_collection:
                    return new_collection.get("id")
                else:
                    logger.error("Failed to create a new collection.")
                    return None
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            sys.exit(1)


def upload_to_linkwarden(
    linkwarden_url, linkwarden_token, collection_id, repo, dry_run=False
):
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }

    link_data = {
        "url": repo.html_url,
        "title": repo.full_name,
        "description": repo.description or "",
        "collectionId": collection_id,
        "tags": [{"name": "GitHub"}, {"name": "Starred"}],
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would upload to Linkwarden: {link_data}")
        return None

    try:
        response = requests.post(
            f"{linkwarden_url}/api/v1/links", headers=headers, json=link_data
        )
        response.raise_for_status()
        return response.json()["id"]
    except requests.RequestException as e:
        logger.error(f"Error uploading {repo.full_name} to Linkwarden: {str(e)}")
        return None


def main():
    args = parse_args()

    # Load environment variables
    load_dotenv()

    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Get environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    github_username = os.getenv("GITHUB_USERNAME")
    linkwarden_url = os.getenv("LINKWARDEN_URL")
    linkwarden_token = os.getenv("LINKWARDEN_TOKEN")

    # Validate environment variables
    if not all([github_username, linkwarden_url, linkwarden_token]):
        logger.error(
            "Missing required environment variables. Please check your .env file."
        )
        sys.exit(1)

    # GitHub setup
    try:
        gh = (
            Github(github_token, retry=config_retry())
            if github_token
            else Github(retry=config_retry())
        )
        user = gh.get_user(github_username)
    except Exception as e:
        logger.error(f"Error connecting to GitHub: {str(e)}")
        sys.exit(1)

    flavour = main_menu
    if flavour == 1:
        collection_id = select_or_create_collection(
            linkwarden_url, linkwarden_token, args.dry_run
        )
        if not collection_id:
            logger.error("Failed to select a collection. Exiting.")
            sys.exit(1)
        existing_links = get_existing_links(
            linkwarden_url, linkwarden_token, collection_id
        )
    else:
        collection_name = input("Enter the name for the new GitHub Stars collection: ")
        collection_id = create_linkwarden_collection(
            linkwarden_url, linkwarden_token, collection_name
        )

        if not collection_id:
            logger.error("Failed to create a new collection. Exiting.")
            sys.exit(1)
        existing_links = set()

    # Process each starred repository
    successful_uploads = 0
    failed_uploads = 0
    skipped_uploads = 0

    for repo in starred_repos(user):
        if repo.html_url in existing_links:
            logger.info(
                f"Skipping {repo.full_name} as it already exists in the collection"
            )
            skipped_uploads += 1
            continue

        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"Processing repository: {repo.full_name}")
                link_id = upload_to_linkwarden(
                    linkwarden_url, linkwarden_token, collection_id, repo, args.dry_run
                )

                if link_id or args.dry_run:
                    logger.info(
                        f"Successfully processed {repo.full_name}"
                        + (f". Link ID: {link_id}" if link_id else "")
                    )
                    successful_uploads += 1
                else:
                    logger.warning(f"Failed to upload {repo.full_name}")
                    failed_uploads += 1
                break
            except requests.exceptions.RequestException as e:
                if e.response is not None and e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", 60)
                    handle_rate_limit(e, retry_after)
                    retry_count += 1
                else:
                    logger.error(
                        f"Error uploading {repo.full_name} to Linkwarden: {str(e)}"
                    )
                    failed_uploads += 1
                    break
            except Exception as e:
                logger.error(f"Unexpected error processing {repo.full_name}: {str(e)}")
                failed_uploads += 1
                break
        else:
            logger.error(
                f"Max retries reached for {repo.full_name}. Moving to next repository."
            )
            failed_uploads += 1
    logger.info("Finished processing all starred repositories.")
    logger.info(f"Successful uploads: {successful_uploads}")
    logger.info(f"Failed uploads: {failed_uploads}")
    logger.info(f"Skipped uploads: {skipped_uploads}")


if __name__ == "__main__":
    main()
