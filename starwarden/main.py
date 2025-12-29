import sys
from http.client import HTTPConnection

import requests
from rich.progress import Progress

from starwarden import config, github_api, linkwarden_api, tui
from starwarden.linkwarden_api import LINK_EXISTS_GLOBALLY
from starwarden.utils import notify
from starwarden.utils.logger import get_logger

logger = get_logger()


def build_tags(config_data, repo):
    if not config_data["opt_tag"]:
        return []

    tags = []

    if config_data["opt_tag_github"]:
        tags.append({"name": "GitHub"})
    if config_data["opt_tag_githubStars"]:
        tags.append({"name": "GitHub Stars"})
    if config_data["opt_tag_language"] and repo.language:
        tags.append({"name": repo.language})
    if config_data["opt_tag_username"]:
        tags.append({"name": config_data["github_username"]})
    if config_data["opt_tag_custom"]:
        for tag in config_data["opt_tag_custom"].split(","):
            if len(tag) > 0:
                tags.append({"name": tag.strip()})

    return tags


def run_update(config_data, collection_id):
    logger.debug(f"Collection ID: {collection_id}")
    existing_links = set(
        linkwarden_api.get_existing_links(config_data["linkwarden_url"], config_data["linkwarden_token"], collection_id)
    )
    logger.info(f"Found {len(existing_links)} existing links in the collection.")
    tui.console.print(
        f"Found {len(existing_links)} existing links in the collection.",
        style="info",
    )

    logger.info("Fetching starred repositories from GitHub...")
    tui.console.print("Fetching starred repositories from GitHub...", style="info")
    total_repos = github_api.get_total_starred_repos(config_data["github_token"], config_data["github_username"])
    logger.info(f"Total starred repositories: {total_repos}")
    tui.console.print(f"Total starred repositories: {total_repos}", style="info")

    successful_uploads = 0
    failed_uploads = 0
    skipped_uploads = 0

    with Progress() as progress:
        task = progress.add_task("Processing starred repos...", total=total_repos, style="info")
        for repo in github_api.get_starred_repos(config_data["github_token"], config_data["github_username"]):
            if repo.html_url in existing_links:
                logger.info(f"Skipping {repo.full_name} as it already exists in the collection")
                skipped_uploads += 1
                progress.update(task, advance=1)
                continue

            max_retries = 3
            retry_count = 0
            tags = build_tags(config_data, repo)

            while retry_count < max_retries:
                try:
                    logger.info(f"Processing repository: {repo.full_name}")
                    link_id = linkwarden_api.upload_link(
                        config_data["linkwarden_url"], config_data["linkwarden_token"], collection_id, repo, tags
                    )

                    if link_id is LINK_EXISTS_GLOBALLY:
                        logger.info(f"Skipping {repo.full_name} as it already exists globally in Linkwarden.")
                        skipped_uploads += 1
                    elif link_id:
                        logger.info(f"Successfully processed {repo.full_name}. Link ID: {link_id}")
                        successful_uploads += 1
                    else:
                        logger.warning(f"Failed to upload {repo.full_name}")
                        failed_uploads += 1
                    break
                except requests.exceptions.RequestException as e:
                    if e.response is not None and e.response.status_code == 429:
                        retry_after = e.response.headers.get("Retry-After", 60)
                        github_api.handle_rate_limit(e, retry_after)
                        retry_count += 1
                    else:
                        logger.error(f"Error uploading {repo.full_name} to Linkwarden: {str(e)}")
                        failed_uploads += 1
                        break
                except Exception as e:
                    logger.error(f"Unexpected error processing {repo.full_name}: {str(e)}")
                    failed_uploads += 1
                    break
            else:
                logger.error(f"Max retries reached for {repo.full_name}. Moving to next repository.")
                failed_uploads += 1

            progress.update(task, advance=1)

    logger.info("Finished processing all starred repositories.")
    logger.info(f"Successful uploads: {successful_uploads}")
    logger.info(f"Failed uploads: {failed_uploads}")
    logger.info(f"Skipped uploads: {skipped_uploads}")

    tui.console.print("\nFinished processing all starred repositories.", style="info")
    tui.console.print(f"Successful uploads: {successful_uploads}", style="info")
    tui.console.print(f"Failed uploads: {failed_uploads}", style="warning")
    tui.console.print(f"Skipped uploads: {skipped_uploads}", style="info")
    notify.send_notification(
        config_data,
        message=f"Successful uploads: {successful_uploads}, failed uploads: {failed_uploads}, skipped_uploads: {skipped_uploads}",
        title="Starwarden Status",
    )


def main():
    args = config.parse_args()
    config_data = config.load_env()
    if args.debug:
        HTTPConnection.debuglevel = 1

    if not args.id:
        tui.display_welcome()
        flavor = tui.main_menu()
        if flavor == 1:
            tui.console.print("Fetching existing collections...", style="info")
            collections = linkwarden_api.get_collections(config_data["linkwarden_url"], config_data["linkwarden_token"])
            collection_id = tui.select_collection(collections)
            if not collection_id:
                logger.error("Failed to select a collection. Exiting.")
                tui.console.print("Failed to select a collection. Exiting.", style="danger")
                return
            run_update(config_data, collection_id)

        elif flavor == 2:
            collection_name = tui.create_collection_prompt()
            logger.info(f"Creating new collection: {collection_name}")
            tui.console.print(f"Creating new collection: {collection_name}", style="info")
            collection = linkwarden_api.create_collection(
                config_data["linkwarden_url"], config_data["linkwarden_token"], collection_name
            )
            if not collection:
                logger.error("Failed to create a new collection. Exiting.")
                tui.console.print("Failed to create a new collection. Exiting.", style="danger")
                return
            collection_id = collection.get("id")
            logger.info(f"Created new collection with ID: {collection_id}")
            tui.console.print(f"Created new collection with ID: {collection_id}", style="info")
            run_update(config_data, collection_id)
        else:
            logger.info("Exiting StarWarden.")
            tui.console.print("Exiting StarWarden. Goodbye!", style="info")
            return
    else:
        run_update(config_data, args.id)


if __name__ == "__main__":
    config_data = config.load_env()
    try:
        main()
    except Exception as e:
        tui.console.print_exception(show_locals=True)
        logger.exception(f"Unexpected error: {str(e)}")
        tui.console.print(f"Unexpected error: {str(e)}", style="danger")
        error_message = f"Starwarden process failed with a critical error: {e}"
        notify.send_notification(config_data, message=error_message, title="Starwarden Process Failure")
        sys.exit(1)
