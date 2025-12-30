from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
import requests

from starwarden.linkwarden_api import LINK_EXISTS_GLOBALLY, get_existing_links, upload_link


@dataclass
class MockRepo:
    """Mock GitHub repository object for testing."""

    full_name: str = "rtuszik/starwarden"
    html_url: str = "https://github.com/rtuszik/starwarden"
    description: str | None = None


@pytest.fixture
def mock_post():
    """Fixture providing a mocked requests.post with configurable response."""
    with patch("starwarden.linkwarden_api.requests.post") as mock:
        mock.response = MagicMock()
        mock.return_value = mock.response
        yield mock


@pytest.fixture
def mock_get():
    """Fixture providing a mocked requests.get."""
    with patch("starwarden.linkwarden_api.requests.get") as mock:
        yield mock


class TestUploadLink:
    def test_description_truncated_when_exceeds_2048_chars(self, mock_post):
        """Descriptions longer than 2048 chars should be truncated with ellipsis."""
        mock_post.response.status_code = 200
        mock_post.response.json.return_value = {"response": {"id": 123, "collectionId": 1}}

        upload_link("https://linkwarden.example.com", "token", 1, MockRepo(description="x" * 3000), [])

        sent_description = mock_post.call_args.kwargs["json"]["description"]
        assert len(sent_description) == 2048
        assert sent_description.endswith("...")

    def test_returns_sentinel_on_409_link_exists(self, mock_post):
        """A 409 response with 'Link already exists' should return LINK_EXISTS_GLOBALLY sentinel."""
        mock_post.response.status_code = 409
        mock_post.response.json.return_value = {"response": "Link already exists"}

        result = upload_link("https://linkwarden.example.com", "token", 1, MockRepo(), [])

        assert result is LINK_EXISTS_GLOBALLY

    def test_upload_link_success_returns_link_id(self, mock_post):
        """Successful upload should return the link ID and send correct payload."""
        mock_post.response.status_code = 200
        mock_post.response.json.return_value = {"response": {"id": 456, "collectionId": 1}}
        repo = MockRepo(description="A test repo")

        result = upload_link("https://linkwarden.example.com", "token", 1, repo, [])

        assert result == 456
        payload = mock_post.call_args.kwargs["json"]
        assert payload["url"] == repo.html_url
        assert payload["title"] == repo.full_name
        assert payload["description"] == "A test repo"
        assert payload["collection"]["id"] == 1

    def test_upload_link_includes_tags_when_provided(self, mock_post):
        """Tags should be included in payload when provided."""
        mock_post.response.status_code = 200
        mock_post.response.json.return_value = {"response": {"id": 789, "collectionId": 1}}
        tags = [{"name": "GitHub"}, {"name": "Python"}]

        upload_link("https://linkwarden.example.com", "token", 1, MockRepo(), tags)

        payload = mock_post.call_args.kwargs["json"]
        assert payload["tags"] == tags

    @pytest.mark.parametrize(
        "scenario,side_effect,status_code,json_response",
        [
            ("missing_id", None, 200, {"response": {}}),
            ("http_error", requests.RequestException("Server error"), None, None),
        ],
        ids=["missing_id_in_response", "http_error"],
    )
    def test_upload_link_returns_none_on_failure(self, mock_post, scenario, side_effect, status_code, json_response):
        """Should return None on various failure conditions."""
        if side_effect:
            mock_post.side_effect = side_effect
        else:
            mock_post.response.status_code = status_code
            mock_post.response.json.return_value = json_response

        result = upload_link("https://linkwarden.example.com", "token", 1, MockRepo(), [])

        assert result is None


class TestGetExistingLinks:
    def test_get_existing_links_yields_all_urls(self, mock_get):
        """Should yield all URLs from a single page response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            {"response": [{"id": 1, "url": "https://a.com"}, {"id": 2, "url": "https://b.com"}]},
            {"response": []},
        ]
        mock_get.return_value = mock_response

        urls = list(get_existing_links("https://lw.example.com", "token", 1))

        assert urls == ["https://a.com", "https://b.com"]

    def test_get_existing_links_pagination_uses_cursor(self, mock_get):
        """Should use cursor from last link ID for pagination."""
        responses = []
        for data in [
            {"response": [{"id": 10, "url": "https://a.com"}, {"id": 20, "url": "https://b.com"}]},
            {"response": [{"id": 30, "url": "https://c.com"}]},
            {"response": []},
        ]:
            resp = MagicMock()
            resp.json.return_value = data
            responses.append(resp)
        mock_get.side_effect = responses

        urls = list(get_existing_links("https://lw.example.com", "token", 1))

        assert urls == ["https://a.com", "https://b.com", "https://c.com"]
        calls = mock_get.call_args_list
        assert calls[0].kwargs["params"]["cursor"] == 0
        assert calls[1].kwargs["params"]["cursor"] == 20
        assert calls[2].kwargs["params"]["cursor"] == 30

    def test_get_existing_links_deduplicates_urls(self, mock_get):
        """Should yield each URL only once even if it appears multiple times."""
        responses = []
        for data in [
            {"response": [{"id": 1, "url": "https://a.com"}, {"id": 2, "url": "https://b.com"}]},
            {"response": [{"id": 3, "url": "https://a.com"}, {"id": 4, "url": "https://b.com"}]},
        ]:
            resp = MagicMock()
            resp.json.return_value = data
            responses.append(resp)
        mock_get.side_effect = responses

        urls = list(get_existing_links("https://lw.example.com", "token", 1))

        assert urls == ["https://a.com", "https://b.com"]
