import pytest

from starwarden.config import load_env


@pytest.fixture
def required_env_vars(monkeypatch):
    """Set required environment variables for config loading."""
    monkeypatch.setenv("GITHUB_USERNAME", "testuser")
    monkeypatch.setenv("LINKWARDEN_URL", "https://linkwarden.example.com")
    monkeypatch.setenv("LINKWARDEN_TOKEN", "test-token-12345")


class TestLoadEnv:
    def test_boolean_env_vars_true_values(self, monkeypatch, required_env_vars):
        """Test that 'true' and '1' are parsed as True for boolean env vars."""
        monkeypatch.setenv("OPT_TAG", "true")
        monkeypatch.setenv("OPT_TAG_GITHUB", "1")
        monkeypatch.setenv("OPT_TAG_GITHUBSTARS", "TRUE")
        monkeypatch.setenv("OPT_TAG_LANGUAGE", "True")

        config = load_env()

        assert config["opt_tag"] is True
        assert config["opt_tag_github"] is True
        assert config["opt_tag_githubStars"] is True
        assert config["opt_tag_language"] is True

    def test_boolean_env_vars_false_values(self, monkeypatch, required_env_vars):
        """Test that other values are parsed as False for boolean env vars."""
        monkeypatch.setenv("OPT_TAG", "false")
        monkeypatch.setenv("OPT_TAG_GITHUB", "0")
        monkeypatch.setenv("OPT_TAG_GITHUBSTARS", "no")
        monkeypatch.setenv("OPT_TAG_LANGUAGE", "")

        config = load_env()

        assert config["opt_tag"] is False
        assert config["opt_tag_github"] is False
        assert config["opt_tag_githubStars"] is False
        assert config["opt_tag_language"] is False

    def test_missing_required_env_vars_exits(self, monkeypatch):
        """Test that missing required env vars causes sys.exit."""
        # Prevent load_dotenv from loading the real .env file
        monkeypatch.setattr("starwarden.config.load_dotenv", lambda: None)
        monkeypatch.delenv("GITHUB_USERNAME", raising=False)
        monkeypatch.delenv("LINKWARDEN_URL", raising=False)
        monkeypatch.delenv("LINKWARDEN_TOKEN", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            load_env()

        assert exc_info.value.code == 1
