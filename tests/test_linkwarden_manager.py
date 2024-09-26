import pytest
import requests
from unittest.mock import Mock, patch
from starwarden import LinkwardenManager, StarwardenError


@pytest.fixture
def linkwarden_manager():
    return LinkwardenManager("https://fake.linkwarden.com", "fake_token")


@patch("starwarden.requests.get")
def test_get_existing_links(mock_get, linkwarden_manager):
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": [
            {"url": "https://github.com/repo1"},
            {"url": "https://github.com/repo2"},
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    links = list(linkwarden_manager.get_existing_links(1))
    assert len(links) == 2
    assert "https://github.com/repo1" in links
    assert "https://github.com/repo2" in links


@patch("starwarden.requests.get")
def test_get_collections(mock_get, linkwarden_manager):
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": [
            {"id": 1, "name": "Collection 1"},
            {"id": 2, "name": "Collection 2"},
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    collections = linkwarden_manager.get_collections()
    assert len(collections) == 2
    assert collections[0]["name"] == "Collection 1"
    assert collections[1]["name"] == "Collection 2"


@patch("starwarden.requests.post")
def test_create_collection(mock_post, linkwarden_manager):
    mock_response = Mock()
    mock_response.json.return_value = {"response": {"id": 3, "name": "New Collection"}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    new_collection = linkwarden_manager.create_collection("New Collection")
    assert new_collection["id"] == 3
    assert new_collection["name"] == "New Collection"


@patch("starwarden.requests.post")
def test_upload_link(mock_post, linkwarden_manager):
    mock_response = Mock()
    mock_response.json.return_value = {"response": {"id": 1, "collectionId": 1}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    mock_repo = Mock(
        html_url="https://github.com/test/repo",
        full_name="test/repo",
        description="Test repo",
    )
    link_id = linkwarden_manager.upload_link(1, mock_repo)
    assert link_id == 1


@patch("starwarden.requests.post")
def test_upload_link_error(mock_post, linkwarden_manager):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.RequestException("API Error")
    mock_post.return_value = mock_response

    mock_repo = Mock(
        html_url="https://github.com/test/repo",
        full_name="test/repo",
        description="Test repo",
    )
    with pytest.raises(StarwardenError):
        linkwarden_manager.upload_link(1, mock_repo)
