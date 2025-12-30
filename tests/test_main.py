from starwarden.main import build_tags


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
