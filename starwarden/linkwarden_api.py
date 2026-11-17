import json

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import Timeout
from urllib3.util.retry import Retry

from starwarden.utils.logger import get_logger

logger = get_logger()

LINK_EXISTS_GLOBALLY = object()


class ExistingLinksError(Exception):
    """Existing links could not be read completely."""


def _retrying_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def get_existing_links(linkwarden_url, linkwarden_token, collection_id):
    url = f"{linkwarden_url.rstrip('/')}/api/v1/links"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    cursor = 0
    seen_links = set()
    with _retrying_session() as session:
        while True:
            try:
                logger.debug(f"Fetching links from cursor {cursor} for collection {collection_id}")
                response = session.get(
                    url,
                    params={"collectionId": collection_id, "cursor": cursor, "sort": 1},
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                logger.error(f"Error fetching links from cursor {cursor}: {e!s}")
                if e.response is not None:
                    logger.error(f"Response status code: {e.response.status_code}")
                    logger.error(f"Response content: {e.response.text}")
                raise ExistingLinksError(f"Could not fetch existing links from cursor {cursor}") from e
            except ValueError as e:
                logger.error(f"Invalid JSON from cursor {cursor}: {e!s}")
                raise ExistingLinksError(f"Invalid response from cursor {cursor}") from e

            links = data.get("response") if isinstance(data, dict) else None
            if not isinstance(links, list) or not all(isinstance(link, dict) and "url" in link for link in links):
                raise ExistingLinksError(f"Unexpected response shape from cursor {cursor}")
            logger.debug(f"Fetched {len(links)} links from cursor {cursor}")

            # empty page = end; duplicate-only page != end
            if not links:
                break

            for link in links:
                if link["url"] not in seen_links:
                    seen_links.add(link["url"])
                    yield link["url"]

            # sort=1 is id asc, so cursor must grow
            next_cursor = links[-1].get("id")
            if not isinstance(next_cursor, int) or next_cursor <= cursor:
                raise ExistingLinksError(f"Pagination did not advance past cursor {cursor}")
            cursor = next_cursor


def get_collections(linkwarden_url, linkwarden_token):
    url = f"{linkwarden_url.rstrip('/')}/api/v1/collections"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        collections = data.get("response", [])
        logger.debug(f"Fetched collections: {json.dumps(collections, indent=2)}")
        return collections
    except requests.RequestException as e:
        raise Exception(f"Error fetching collections from Linkwarden: {e!s}") from e


def create_collection(linkwarden_url, linkwarden_token, name, description=""):
    url = f"{linkwarden_url.rstrip('/')}/api/v1/collections"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    data = {"name": name, "description": description}
    try:
        logger.debug(f"Attempting to create collection: {name}")
        response = requests.post(
            url,
            headers=headers,
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
        logger.error("Request timed out while creating new collection in Linkwarden")
        return None
    except requests.RequestException as e:
        logger.error(f"Error creating new collection in Linkwarden: {e!s}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")
        return None


def upload_link(linkwarden_url, linkwarden_token, collection_id, repo, tags):
    description = repo.description or ""
    if len(description) > 2048:
        description = f"{description[:2045]}..."
    link_data = {
        "url": repo.html_url,
        "title": repo.full_name,
        "description": description,
        "collection": {"id": collection_id},
    }
    if tags:
        link_data["tags"] = tags

    url = f"{linkwarden_url.rstrip('/')}/api/v1/links"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    logger.debug(f"Sending link data to Linkwarden: {json.dumps(link_data, indent=2)}")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=link_data,
            timeout=30,
        )
        # Check for 409 Conflict
        if response.status_code == 409:
            response_json = response.json()
            if response_json.get("response") == "Link already exists":
                logger.info(f"Link for {repo.full_name} already exists in Linkwarden (status 409).")
                return LINK_EXISTS_GLOBALLY

        response.raise_for_status()
        response_json = response.json()

        logger.debug(f"API response for {repo.full_name}: {json.dumps(response_json, indent=2)}")

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
            logger.error(f"Unexpected response format for {repo.full_name}. Response: {response_json}")
            return None

    except requests.RequestException as e:
        logger.error(f"Error uploading {repo.full_name} to Linkwarden: {e!s}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")

        return None
