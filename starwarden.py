import json
import logging
import os
import sys
import time
from argparse import ArgumentParser
from logging.handlers import RotatingFileHandler
from math import ceil

import requests
from dotenv import load_dotenv
from github import Github, GithubException, RateLimitExceededException
from requests.exceptions import Timeout
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Prompt
from urllib3 import Retry

logger = logging.getLogger(__name__)

console = Console()

MAX_RETRIES = 3
RETRY_DELAY = 5


def configure_logging(debug=False):
    log_level = logging.DEBUG if debug else logging.INFO
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    log_file = "starwarden.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)


class GithubStarManager:
    def __init__(self, github_token, github_username):
        self.gh = (
            Github(github_token, retry=self.config_retry())
            if github_token
            else Github(retry=self.config_retry())
        )
        self.user = self.gh.get_user(github_username)

    @staticmethod
    def config_retry(backoff_factor=1.0, total=8):
        Retry.DEFAULT_BACKOFF_MAX = backoff_factor * 2 ** (total - 1)
        return Retry(total=total, backoff_factor=backoff_factor)

    def starred_repos(self):
        starred = self.user.get_starred()
        total_pages = ceil(starred.totalCount / 30)

        for page_num in range(0, total_pages):
            while True:
                try:
                    for repo in starred.get_page(page_num):
                        yield repo
                    break
                except RateLimitExceededException as e:
                    self.handle_rate_limit(e)
                except GithubException as e:
                    if e.status == 403 and "rate limit" in str(e).lower():
                        self.handle_rate_limit(e)
                    else:
                        logger.error(f"GitHub API error: {str(e)}")
                        raise

    @staticmethod
    def handle_rate_limit(e, retry_after=None):
        if retry_after is None:
            retry_after = e.headers.get("Retry-After", 60)

        retry_after = int(retry_after)
        logger.warning(
            f"Rate limit exceeded. Waiting for {retry_after} seconds before retrying."
        )
        time.sleep(retry_after)


class LinkwardenManager:
    def __init__(self, linkwarden_url, linkwarden_token):
        if not linkwarden_url or not linkwarden_token:
            raise ValueError("Linkwarden URL and token must be provided")
        self.linkwarden_url = linkwarden_url.rstrip("/") + "/api/v1"
        self.linkwarden_token = linkwarden_token
        self.headers = {
            "Authorization": f"Bearer {linkwarden_token}",
            "Content-Type": "application/json",
        }

    def get_existing_links(self, collection_id):
        page = 1
        seen_links = set()
        while True:
            try:
                logger.debug(
                    f"Fetching links from page {page} for collection {collection_id}"
                )
                response = requests.get(
                    f"{self.linkwarden_url}/links",
                    params={"collectionId": collection_id, "page": page},
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                links = data.get("response", [])
                logger.debug(f"Fetched {len(links)} links from page {page}")

                new_links = [
                    link["url"] for link in links if link["url"] not in seen_links
                ]
                if not new_links:
                    logger.info(
                        f"No new links found on page {page}. Stopping pagination."
                    )
                    break

                seen_links.update(new_links)
                yield from new_links
                page += 1
            except requests.RequestException as e:
                logger.error(f"Error fetching links from page {page}: {str(e)}")
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response content: {e.response.text}")
                break

    def get_collections(self):
        try:
            response = requests.get(
                f"{self.linkwarden_url}/collections",
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            collections = data.get("response", [])
            logger.debug(f"Fetched collections: {json.dumps(collections, indent=2)}")
            return collections
        except requests.RequestException as e:
            raise StarwardenError(
                f"Error fetching collections from Linkwarden: {str(e)}"
            )

    def create_collection(self, name, description=""):
        data = {"name": name, "description": description}
        try:
            logger.debug(f"Attempting to create collection: {name}")
            response = requests.post(
                f"{self.linkwarden_url}/collections",
                headers=self.headers,
                json=data,
                timeout=30,
            )
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            response.raise_for_status()
            created_collection = response.json().get("response", {})
            logger.info(f"Created collection: {created_collection}")
            return created_collection
        except Timeout:
            logger.error(
                "Request timed out while creating new collection in Linkwarden"
            )
            return None
        except requests.RequestException as e:
            logger.error(f"Error creating new collection in Linkwarden: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            return None

    def upload_link(self, collection_id, repo):
        link_data = {
            "url": repo.html_url,
            "title": repo.full_name,
            "description": repo.description or "",
            "collection": {"id": collection_id},
            "tags": [{"name": "GitHub"}, {"name": "GitHub Stars"}],
        }

        logger.debug(
            f"Sending link data to Linkwarden: {json.dumps(link_data, indent=2)}"
        )

        try:
            response = requests.post(
                f"{self.linkwarden_url}/links",
                headers=self.headers,
                json=link_data,
            )
            response.raise_for_status()
            response_json = response.json()

            logger.debug(
                f"API response for {repo.full_name}: {json.dumps(response_json, indent=2)}"
            )

            created_link = response_json.get("response", {})
            if created_link and "id" in created_link:
                returned_collection_id = created_link.get("collectionId")
                if returned_collection_id != collection_id:
                    logger.warning(
                        f"Link created in collection {returned_collection_id} instead of requested collection {collection_id}"
                    )
                logger.info(
                    f"Successfully created link for {repo.full_name}. Link ID: {created_link['id']}, Collection ID: {returned_collection_id}"
                )
                return created_link["id"]
            else:
                logger.error(
                    f"Unexpected response format for {repo.full_name}. Response: {response_json}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Error uploading {repo.full_name} to Linkwarden: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.content}")

            return None


class StarwardenApp:
    def __init__(self):
        self.args = self.parse_args()
        self.load_env()
        self.setup_logging()
        self.github_manager = GithubStarManager(self.github_token, self.github_username)
        self.linkwarden_manager = LinkwardenManager(
            self.linkwarden_url, self.linkwarden_token
        )

    @staticmethod
    def parse_args():
        parser = ArgumentParser(
            description="Export GitHub starred repositories as individual links to Linkwarden"
        )
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        return parser.parse_args()

    def load_env(self):
        load_dotenv()
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_username = os.getenv("GITHUB_USERNAME")
        self.linkwarden_url = os.getenv("LINKWARDEN_URL")
        self.linkwarden_token = os.getenv("LINKWARDEN_TOKEN")

        if not all([self.github_username, self.linkwarden_url, self.linkwarden_token]):
            logger.error(
                "Missing required environment variables. Please check your .env file."
            )
            sys.exit(1)

    def setup_logging(self):
        if self.args.debug:
            logger.setLevel(logging.DEBUG)

    def display_welcome(self):
        welcome_text = r"""
     _______.___________.    ___      .______     ____    __    ____  ___      .______       _______   _______ .__   __. 
    /       |           |   /   \     |   _  \    \   \  /  \  /   / /   \     |   _  \     |       \ |   ____||  \ |  | 
   |   (----`---|  |----`  /  ^  \    |  |_)  |    \   \/    \/   / /  ^  \    |  |_)  |    |  .--.  ||  |__   |   \|  | 
    \   \       |  |      /  /_\  \   |      /      \            / /  /_\  \   |      /     |  |  |  ||   __|  |  . `  | 
.----)   |      |  |     /  _____  \  |  |\  \----.  \    /\    / /  _____  \  |  |\  \----.|  '--'  ||  |____ |  |\   | 
|_______/       |__|    /__/     \__\ | _| `._____|   \__/  \__/ /__/     \__\ | _| `._____||_______/ |_______||__| \__| 
                                                                                                                         
        """
        console.print(Panel(welcome_text, expand=True, border_style="bold blue"))

    def main_menu(self):
        options = [
            "Update existing GitHub Stars collection",
            "Create a new GitHub Stars collection",
            "Exit",
        ]
        console.print("[bold cyan]Choose an option:[/bold cyan]")
        for i, option in enumerate(options, 1):
            console.print(f"  {i}. {option}")

        choice = Prompt.ask(
            "Enter your choice", choices=[str(i) for i in range(1, len(options) + 1)]
        )
        return int(choice)

    def select_or_create_collection(self):
        collections = self.linkwarden_manager.get_collections()
        if collections is None or not collections:
            console.print(
                "[bold red]No collections found or failed to fetch collections.[/bold red]"
            )
            return None

        logger.info("Fetching existing collections...")
        console.print("[bold cyan]Available collections:[/bold cyan]")
        for i, collection in enumerate(collections, 1):
            console.print(
                f"  {i}. [green]{collection.get('name', 'Unnamed')}[/green] (ID: {collection.get('id', 'Unknown')}) - {collection.get('description', 'No description')}"
            )

        choice = Prompt.ask(
            "Enter the number of your choice",
            choices=[str(i) for i in range(1, len(collections) + 1)],
        )
        selected = collections[int(choice) - 1]
        logger.info(
            f"Selected collection: {selected.get('name')} (ID: {selected.get('id')})"
        )
        return selected.get("id")

    def run(self):
        self.display_welcome()
        flavor = self.main_menu()
        if flavor == 1:
            console.print("[bold cyan]Fetching existing collections...[/bold cyan]")
            collection_id = self.select_or_create_collection()
            if not collection_id:
                logger.error("Failed to select a collection. Exiting.")
                console.print(
                    "[bold red]Failed to select a collection. Exiting.[/bold red]"
                )
                return

            console.print(f"[green]Selected collection ID: {collection_id}[/green]")

            console.print(
                "[bold cyan]Fetching existing links in the collection...[/bold cyan]"
            )
            existing_links = set(
                self.linkwarden_manager.get_existing_links(collection_id)
            )
            logger.info(
                f"Found {len(existing_links)} existing links in the collection."
            )
            console.print(
                f"[green]Found {len(existing_links)} existing links in the collection.[/green]"
            )
        elif flavor == 2:
            collection_name = Prompt.ask(
                "Enter the name for the new GitHub Stars collection"
            )
            logger.info(f"Creating new collection: {collection_name}")
            console.print(
                f"[bold cyan]Creating new collection: {collection_name}[/bold cyan]"
            )
            collection = self.linkwarden_manager.create_collection(collection_name)
            if not collection:
                logger.error("Failed to create a new collection. Exiting.")
                console.print(
                    "[bold red]Failed to create a new collection. Exiting.[/bold red]"
                )
                return
            collection_id = collection.get("id")
            logger.info(f"Created new collection with ID: {collection_id}")
            console.print(
                f"[green]Created new collection with ID: {collection_id}[/green]"
            )
            existing_links = set()
        else:
            logger.info("Exiting StarWarden.")
            console.print("[bold red]Exiting StarWarden. Goodbye![/bold red]")
            return

        logger.info("Fetching starred repositories from GitHub...")
        console.print(
            "[bold cyan]Fetching starred repositories from GitHub...[/bold cyan]"
        )
        total_repos = self.github_manager.user.get_starred().totalCount
        logger.info(f"Total starred repositories: {total_repos}")
        console.print(f"[green]Total starred repositories: {total_repos}[/green]")

        successful_uploads = 0
        failed_uploads = 0
        skipped_uploads = 0

        with Progress() as progress:
            task = progress.add_task(
                "[cyan]Processing starred repos...", total=total_repos
            )
            for repo in self.github_manager.starred_repos():
                if repo.html_url in existing_links:
                    logger.info(
                        f"Skipping {repo.full_name} as it already exists in the collection"
                    )
                    skipped_uploads += 1
                    progress.update(task, advance=1)
                    continue

                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        logger.info(f"Processing repository: {repo.full_name}")
                        link_id = self.linkwarden_manager.upload_link(
                            collection_id, repo
                        )

                        if link_id:
                            logger.info(
                                f"Successfully processed {repo.full_name}. Link ID: {link_id}"
                            )
                            successful_uploads += 1
                        else:
                            logger.warning(f"Failed to upload {repo.full_name}")
                            failed_uploads += 1
                        break
                    except requests.exceptions.RequestException as e:
                        if e.response is not None and e.response.status_code == 429:
                            retry_after = e.response.headers.get("Retry-After", 60)
                            self.github_manager.handle_rate_limit(e, retry_after)
                            retry_count += 1
                        else:
                            logger.error(
                                f"Error uploading {repo.full_name} to Linkwarden: {str(e)}"
                            )
                            failed_uploads += 1
                            break
                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing {repo.full_name}: {str(e)}"
                        )
                        failed_uploads += 1
                        break
                else:
                    logger.error(
                        f"Max retries reached for {repo.full_name}. Moving to next repository."
                    )
                    failed_uploads += 1

                progress.update(task, advance=1)

        logger.info("Finished processing all starred repositories.")
        logger.info(f"Successful uploads: {successful_uploads}")
        logger.info(f"Failed uploads: {failed_uploads}")
        logger.info(f"Skipped uploads: {skipped_uploads}")

        console.print(
            "\n[bold green]Finished processing all starred repositories.[/bold green]"
        )
        console.print(f"[green]Successful uploads: {successful_uploads}[/green]")
        console.print(f"[yellow]Failed uploads: {failed_uploads}[/yellow]")
        console.print(f"[cyan]Skipped uploads: {skipped_uploads}[/cyan]")


class StarwardenError(Exception):
    """Base exception class for Starwarden application"""
    pass


if __name__ == "__main__":
    try:
        configure_logging()
        app = StarwardenApp()
        app.run()
    except StarwardenError as e:
        logger.error(f"Starwarden error: {str(e)}")
        console.print(f"[bold red]Starwarden error: {str(e)}[/bold red]")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")
        sys.exit(1)
