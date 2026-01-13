import json

import requests
from requests.exceptions import Timeout

from starwarden.utils.logger import get_logger

logger = get_logger()

LINK_EXISTS_GLOBALLY = object()


def get_existing_links(linkwarden_url, linkwarden_token, collection_id, delete_duplicate=False):
    url = f"{linkwarden_url.rstrip('/')}/api/v1/search"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    cursor = None
    seen_urls = set()
    duplicate_link_ids = []
    total_links_processed = 0
    
    while True:
        try:
            logger.debug(f"Fetching links from cursor {cursor} for collection {collection_id}")
            params = {"collectionId": collection_id, "sort": 1}
            if cursor is not None:
                params["cursor"] = cursor
                
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()    
            links = data.get("data", {}).get("links", [])
            next_cursor = data.get("data", {}).get("nextCursor")
            
            logger.debug(f"Fetched {len(links)} links from cursor {cursor}")
            total_links_processed += len(links)
            
            for link in links:
                link_url = link["url"]
                link_id = link["id"]
                
                if link_url in seen_urls:
                    # Found a duplicate
                    logger.debug(f"Found duplicate link: {link_url} (ID: {link_id})")
                    duplicate_link_ids.append(link_id)
                else:
                    seen_urls.add(link_url)
                
                yield link_url

            if next_cursor is None:
                logger.info("Reached end of pagination (no nextCursor in response)")
                break
            else:
                cursor = next_cursor
                logger.debug(f"Advancing to next cursor: {cursor}")

        except requests.RequestException as e:
            logger.error(f"Error fetching links from cursor {cursor}: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            break
    
    # Handle duplicate deletion if requested
    if delete_duplicate and duplicate_link_ids:
        logger.info(f"Found {len(duplicate_link_ids)} duplicate links to delete: {duplicate_link_ids}")
        
        batch_size = 100
        total_deleted = 0
        
        for i in range(0, len(duplicate_link_ids), batch_size):
            batch = duplicate_link_ids[i:i + batch_size]
            logger.debug(f"Deleting batch {i//batch_size + 1}: {len(batch)} links")
            
            deleted_count = delete_links(linkwarden_url, linkwarden_token, batch)
            if deleted_count is not None:
                total_deleted += deleted_count
            else:
                logger.error(f"Failed to delete batch {i//batch_size + 1}")
        
        logger.info(f"Successfully deleted {total_deleted} duplicate links out of {len(duplicate_link_ids)} found")
        logger.info(f"Processed {total_links_processed} total links in collection {collection_id}")


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
        raise Exception(f"Error fetching collections from Linkwarden: {str(e)}") from e


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
        logger.error(f"Error creating new collection in Linkwarden: {str(e)}")
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
        logger.error(f"Error uploading {repo.full_name} to Linkwarden: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")

        return None


def delete_links(linkwarden_url, linkwarden_token, link_ids):
    url = f"{linkwarden_url.rstrip('/')}/api/v1/links"
    headers = {
        "Authorization": f"Bearer {linkwarden_token}",
        "Content-Type": "application/json",
    }
    
    request_data = {
        "linkIds": link_ids
    }
    
    logger.debug(f"Attempting to delete {len(link_ids)} links: {link_ids}")
    
    try:
        response = requests.delete(
            url,
            headers=headers,
            json=request_data,
            timeout=30,
        )
        
        logger.debug(f"Delete response status code: {response.status_code}")
        logger.debug(f"Delete response content: {response.text}")
        
        if response.status_code == 401:
            logger.error("Unauthorized: Invalid or expired token for delete operation")
            return None
        
        response.raise_for_status()
        response_json = response.json()
        
        deleted_count = response_json.get("response", {}).get("count", 0)
        
        logger.info(f"Successfully deleted {deleted_count} links out of {len(link_ids)} requested")
        
        if deleted_count != len(link_ids):
            logger.warning(f"Expected to delete {len(link_ids)} links, but only {deleted_count} were deleted")
        
        return deleted_count
        
    except Timeout:
        logger.error("Request timed out while deleting links")
        return None
    except requests.RequestException as e:
        logger.error(f"Error deleting links from Linkwarden: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")
        return None