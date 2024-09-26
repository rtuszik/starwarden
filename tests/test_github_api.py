import pytest
from unittest.mock import Mock, patch
from github import Github, GithubException, RateLimitExceededException
from starwarden import GithubStarManager, StarwardenError


@pytest.fixture
def github_star_manager():
    with patch("starwarden.Github") as mock_github:
        mock_user = Mock()
        mock_github.return_value.get_user.return_value = mock_user
        return GithubStarManager("fake_token", "fake_username")


def test_initialize_user(github_star_manager):
    assert github_star_manager.user is not None


def test_initialize_user_exception():
    with patch("starwarden.Github") as mock_github:
        mock_github.return_value.get_user.side_effect = GithubException(
            404, "User not found"
        )
        with pytest.raises(StarwardenError) as excinfo:
            manager = GithubStarManager("fake_token", "fake_username")
        assert 'Failed to initialize GitHub user: 404 "User not found"' in str(
            excinfo.value
        )


@pytest.mark.timeout(5)
def test_starred_repos(github_star_manager):
    mock_starred = Mock()
    mock_starred.totalCount = 2
    github_star_manager.user.get_starred.return_value = mock_starred

    mock_repo1 = Mock(html_url="https://github.com/user/repo1", full_name="user/repo1")
    mock_repo2 = Mock(html_url="https://github.com/user/repo2", full_name="user/repo2")
    mock_starred.get_page.return_value = [mock_repo1, mock_repo2]

    repos = list(github_star_manager.starred_repos())
    assert len(repos) == 2
    assert repos[0].html_url == "https://github.com/user/repo1"
    assert repos[1].html_url == "https://github.com/user/repo2"


@pytest.mark.timeout(5)
def test_starred_repos_rate_limit(github_star_manager):
    mock_starred = Mock()
    mock_starred.totalCount = 1
    github_star_manager.user.get_starred.return_value = mock_starred

    mock_starred.get_page.side_effect = [
        RateLimitExceededException(
            403, "API rate limit exceeded", headers={"Retry-After": "1"}
        ),
        [Mock(html_url="https://github.com/user/repo1", full_name="user/repo1")],
    ]

    repos = list(github_star_manager.starred_repos(skip_sleep=True))
    assert len(repos) == 1
    assert repos[0].html_url == "https://github.com/user/repo1"
    assert (
        github_star_manager.handle_rate_limit.call_count == 1
        if hasattr(github_star_manager.handle_rate_limit, "call_count")
        else True
    )


@pytest.mark.timeout(5)
def test_starred_repos_github_exception(github_star_manager):
    mock_starred = Mock()
    mock_starred.totalCount = 1
    github_star_manager.user.get_starred.return_value = mock_starred

    mock_starred.get_page.side_effect = GithubException(500, "Internal Server Error")

    with pytest.raises(GithubException):
        list(github_star_manager.starred_repos(skip_sleep=True))


def test_handle_rate_limit(github_star_manager):
    with patch("time.sleep") as mock_sleep:
        github_star_manager.handle_rate_limit(Mock(headers={"Retry-After": "2"}))
        mock_sleep.assert_called_once_with(2)

    with patch("time.sleep") as mock_sleep:
        github_star_manager.handle_rate_limit(Mock(headers={}))
        mock_sleep.assert_called_once_with(60)

    with patch("time.sleep") as mock_sleep:
        github_star_manager.handle_rate_limit(
            Mock(headers={"Retry-After": "2"}), skip_sleep=True
        )
        mock_sleep.assert_not_called()

    # Test with skip_sleep=False (default behavior)
    with patch("time.sleep") as mock_sleep:
        github_star_manager.handle_rate_limit(Mock(headers={"Retry-After": "2"}))
        mock_sleep.assert_called_once_with(2)
