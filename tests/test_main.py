from unittest.mock import patch

from starwarden.linkwarden_api import ExistingLinksError
from starwarden.main import build_tags, run_update


class MockRepo:
    """Mock GitHub repository object for testing."""

    def __init__(self, language=None):
        self.language = language


class TestBuildTags:
    def test_returns_empty_when_opt_tag_disabled(self):
        """When opt_tag is False, no tags should be returned."""
        config = {
            "opt_tag": False,
            "opt_tag_github": True,
            "opt_tag_githubStars": True,
            "opt_tag_language": True,
            "opt_tag_username": True,
            "opt_tag_custom": "custom",
            "github_username": "testuser",
        }

        result = build_tags(config, MockRepo(language="Python"))

        assert result == []

    def test_all_tag_options_combined(self):
        """Test all tag types are properly combined."""
        config = {
            "opt_tag": True,
            "opt_tag_github": True,
            "opt_tag_githubStars": True,
            "opt_tag_language": True,
            "opt_tag_username": True,
            "opt_tag_custom": "tag1, tag2",
            "github_username": "testuser",
        }

        result = build_tags(config, MockRepo(language="Zig"))

        assert result == [
            {"name": "GitHub"},
            {"name": "GitHub Stars"},
            {"name": "Zig"},
            {"name": "testuser"},
            {"name": "tag1"},
            {"name": "tag2"},
        ]


class TestRunUpdate:
    def test_skips_run_when_existing_links_cannot_be_read(self):
        """No GitHub fetch and no upload when the existing links are incomplete."""
        config = {"linkwarden_url": "https://lw.example.com", "linkwarden_token": "token"}

        def failing(*args, **kwargs):
            yield "https://a.com"
            raise ExistingLinksError("Could not fetch existing links from cursor 1")

        with (
            patch("starwarden.main.linkwarden_api.get_existing_links", side_effect=failing),
            patch("starwarden.main.github_api.get_total_starred_repos") as total,
            patch("starwarden.main.linkwarden_api.upload_link") as upload,
        ):
            run_update(config, 1)

        total.assert_not_called()
        upload.assert_not_called()
