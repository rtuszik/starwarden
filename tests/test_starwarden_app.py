import pytest
import logging
import requests
from unittest.mock import Mock, patch
from starwarden import (
    StarwardenApp,
    StarwardenError,
    configure_logging,
    GithubStarManager,
    LinkwardenManager,
    check_test_coverage,
)
from github import GithubException


@pytest.fixture
def starwarden_app():
    with patch("starwarden.GithubStarManager"), patch(
        "starwarden.LinkwardenManager"
    ), patch("sys.argv", ["starwarden.py"]):  # Simulate no command-line arguments
        app = StarwardenApp()
        app.github_manager = Mock()
        app.linkwarden_manager = Mock()
        return app


def test_parse_args(starwarden_app):
    with patch("sys.argv", ["starwarden.py", "--debug"]):
        args = starwarden_app.parse_args()
        assert args.debug is True


def test_load_env(starwarden_app):
    with patch.dict(
        "os.environ",
        {
            "GITHUB_TOKEN": "fake_token",
            "GITHUB_USERNAME": "fake_user",
            "LINKWARDEN_URL": "https://fake.linkwarden.com",
            "LINKWARDEN_TOKEN": "fake_linkwarden_token",
        },
    ):
        starwarden_app.load_env()
        assert starwarden_app.github_token == "fake_token"
        assert starwarden_app.github_username == "fake_user"
        assert starwarden_app.linkwarden_url == "https://fake.linkwarden.com"
        assert starwarden_app.linkwarden_token == "fake_linkwarden_token"


@patch("starwarden.console.print")
def test_display_welcome(mock_print, starwarden_app):
    starwarden_app.display_welcome()
    mock_print.assert_called()


@patch("starwarden.Prompt.ask")
def test_main_menu(mock_ask, starwarden_app):
    mock_ask.return_value = "1"
    choice = starwarden_app.main_menu()
    assert choice == 1


@patch("starwarden.Prompt.ask")
def test_select_or_create_collection(mock_ask, starwarden_app):
    starwarden_app.linkwarden_manager.get_collections.return_value = [
        {"id": 1, "name": "Collection 1", "_count": {"links": 10}},
        {"id": 2, "name": "Collection 2", "_count": {"links": 20}},
    ]
    mock_ask.return_value = "1"
    collection_id = starwarden_app.select_or_create_collection()
    assert collection_id == 1


@patch("starwarden.console.print")
def test_run(mock_print, starwarden_app):
    starwarden_app.args.id = 1
    starwarden_app.linkwarden_manager.get_existing_links.return_value = [
        "https://github.com/repo1"
    ]
    starwarden_app.github_manager.user.get_starred.return_value.totalCount = 2
    mock_repo1 = Mock(html_url="https://github.com/repo1", full_name="user/repo1")
    mock_repo2 = Mock(html_url="https://github.com/repo2", full_name="user/repo2")
    starwarden_app.github_manager.starred_repos.return_value = [mock_repo1, mock_repo2]
    starwarden_app.linkwarden_manager.upload_link.return_value = 1

    starwarden_app.run()

    assert starwarden_app.linkwarden_manager.upload_link.call_count == 1
    assert starwarden_app.linkwarden_manager.get_existing_links.call_count == 1
    assert starwarden_app.linkwarden_manager.get_existing_links.call_args == ((1,),)
    assert starwarden_app.github_manager.user.get_starred.call_count == 1
    assert starwarden_app.github_manager.starred_repos.call_count == 1
    assert mock_print.call_count > 0


def test_starwarden_error():
    with pytest.raises(StarwardenError):
        raise StarwardenError("Test error")


@patch("starwarden.Prompt.ask")
def test_main_menu_exit(mock_ask, starwarden_app):
    mock_ask.return_value = "3"
    choice = starwarden_app.main_menu()
    assert choice == 3


@patch("starwarden.Prompt.ask")
def test_select_or_create_collection_new(mock_ask, starwarden_app, caplog):
    caplog.set_level(logging.DEBUG)

    # Test case for creating a new collection
    starwarden_app.linkwarden_manager.get_collections.return_value = []
    mock_ask.side_effect = ["new_collection"]
    starwarden_app.linkwarden_manager.create_collection.return_value = {"id": 1}

    collection_id = starwarden_app.select_or_create_collection()

    assert collection_id == 1
    assert "Successfully created new collection with ID: 1" in caplog.text
    starwarden_app.linkwarden_manager.create_collection.assert_called_once_with(
        "new_collection"
    )

    # Reset mocks and logs
    mock_ask.reset_mock()
    starwarden_app.linkwarden_manager.create_collection.reset_mock()
    caplog.clear()

    # Test case when create_collection doesn't return a dict with 'id'
    starwarden_app.linkwarden_manager.get_collections.return_value = []
    mock_ask.side_effect = ["another_new_collection"]
    starwarden_app.linkwarden_manager.create_collection.return_value = None
    collection_id = starwarden_app.select_or_create_collection()

    assert collection_id is None
    assert "Failed to create new collection." in caplog.text

    assert collection_id is None
    assert "Failed to create new collection. Received: None" in caplog.text
    starwarden_app.linkwarden_manager.create_collection.assert_called_once_with(
        "another_new_collection"
    )


@patch("starwarden.console.print")
@patch("starwarden.Prompt.ask")
def test_run_with_new_collection(mock_ask, mock_print, starwarden_app):
    starwarden_app.args.id = None
    mock_ask.return_value = "new_collection"
    with patch.object(starwarden_app, "main_menu", return_value=2), patch.object(
        starwarden_app, "select_or_create_collection", return_value=1
    ):
        starwarden_app.linkwarden_manager.get_existing_links.return_value = []
        starwarden_app.github_manager.user.get_starred.return_value.totalCount = 1
        mock_repo = Mock(html_url="https://github.com/repo1", full_name="user/repo1")
        starwarden_app.github_manager.starred_repos.return_value = [mock_repo]
        starwarden_app.linkwarden_manager.upload_link.return_value = 1
        starwarden_app.linkwarden_manager.create_collection.return_value = {"id": 1}

        starwarden_app.run()

        assert starwarden_app.linkwarden_manager.upload_link.call_count == 1
        assert starwarden_app.linkwarden_manager.get_existing_links.call_count == 1
        starwarden_app.linkwarden_manager.get_existing_links.assert_called_with(1)
        starwarden_app.github_manager.user.get_starred.assert_called_once()
        starwarden_app.github_manager.starred_repos.assert_called_once()
        mock_print.assert_called()
        mock_ask.assert_called_once_with(
            "Enter the name for the new GitHub Stars collection"
        )
        starwarden_app.linkwarden_manager.create_collection.assert_called_once_with(
            "new_collection"
        )


def test_setup_logging(starwarden_app):
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        starwarden_app.args.debug = True
        starwarden_app.setup_logging()

        mock_get_logger.assert_called_once_with()
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

        # Test with debug=False
        mock_get_logger.reset_mock()
        mock_logger.reset_mock()
        starwarden_app.args.debug = False
        starwarden_app.setup_logging()

        mock_get_logger.assert_not_called()
        mock_logger.setLevel.assert_not_called()


@pytest.mark.usefixtures("caplog")
@patch("starwarden.requests.RequestException", new_callable=Exception)
def test_run_with_request_exception(mock_exception, starwarden_app, caplog):
    starwarden_app.args.id = 1
    starwarden_app.linkwarden_manager.get_existing_links.return_value = []
    starwarden_app.github_manager.user.get_starred.return_value.totalCount = 1
    mock_repo = Mock(html_url="https://github.com/repo1", full_name="user/repo1")
    starwarden_app.github_manager.starred_repos.return_value = [mock_repo]
    starwarden_app.linkwarden_manager.upload_link.side_effect = mock_exception

    starwarden_app.run()
    # Assert that the exception was logged
    assert any(
        "Unexpected error processing user/repo1" in record.message
        for record in caplog.records
    )


def test_configure_logging(caplog):
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        configure_logging(debug=True)

        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        assert mock_logger.addHandler.called

        # Test with debug=False
        mock_logger.reset_mock()
        configure_logging(debug=False)

        mock_logger.setLevel.assert_called_once_with(logging.INFO)
        assert mock_logger.addHandler.called


@patch("starwarden.StarwardenApp.display_welcome")
@patch("starwarden.StarwardenApp.main_menu")
@patch("starwarden.StarwardenApp.select_or_create_collection")
def test_run_with_no_id(mock_select, mock_menu, mock_welcome, starwarden_app):
    starwarden_app.args.id = None
    mock_menu.return_value = 1
    mock_select.return_value = 1
    starwarden_app.linkwarden_manager.get_existing_links.return_value = []
    starwarden_app.github_manager.user.get_starred.return_value.totalCount = 0
    starwarden_app.github_manager.starred_repos.return_value = []

    starwarden_app.run()

    mock_welcome.assert_called_once()
    mock_menu.assert_called_once()
    mock_select.assert_called_once()


@patch("starwarden.StarwardenApp.main_menu")
def test_run_with_exit_option(mock_menu, starwarden_app):
    starwarden_app.args.id = None
    mock_menu.return_value = 3

    starwarden_app.run()

    mock_menu.assert_called_once()
    starwarden_app.linkwarden_manager.get_existing_links.assert_not_called()
    starwarden_app.github_manager.user.get_starred.assert_not_called()
    starwarden_app.github_manager.starred_repos.assert_not_called()


@patch("starwarden.requests.post")
def test_linkwarden_manager_upload_link_failure(mock_post):
    linkwarden_manager = LinkwardenManager("https://fake.linkwarden.com", "fake_token")
    mock_post.side_effect = requests.RequestException("API Error")
    mock_repo = Mock(
        html_url="https://github.com/test/repo",
        full_name="test/repo",
        description="Test repo",
    )

    with pytest.raises(StarwardenError) as excinfo:
        linkwarden_manager.upload_link(1, mock_repo)

    assert "Failed to upload test/repo to Linkwarden" in str(excinfo.value)

    assert "Failed to upload test/repo to Linkwarden" in str(excinfo.value)


@patch("starwarden.Github")
def test_github_star_manager_initialization_failure(mock_github):
    mock_github.return_value.get_user.side_effect = GithubException(
        404, "User not found"
    )

    with pytest.raises(StarwardenError) as excinfo:
        GithubStarManager("fake_token", "fake_username")
    assert 'Failed to initialize GitHub user: 404 "User not found"' in str(
        excinfo.value
    )


def test_initialize_user_error_handling():
    with patch("starwarden.Github") as mock_github, patch(
        "starwarden.ArgumentParser.parse_args"
    ) as mock_parse_args:
        mock_github.return_value.get_user.side_effect = Exception("Test error")
        mock_parse_args.return_value = Mock(debug=False, id=None)

        with pytest.raises(StarwardenError) as excinfo:
            StarwardenApp()

        assert "Failed to initialize GitHub user: Test error" in str(excinfo.value)


@patch("pytest.main")
@patch("coverage.Coverage")
def test_check_test_coverage(mock_coverage, mock_pytest_main):
    mock_coverage_instance = Mock()
    mock_coverage.return_value = mock_coverage_instance
    mock_pytest_main.return_value = 0

    with patch("starwarden.console.print") as mock_print:
        check_test_coverage()

    mock_coverage_instance.start.assert_called_once()
    mock_pytest_main.assert_called_once_with(["-v", "tests"])
    mock_coverage_instance.stop.assert_called_once()
    mock_coverage_instance.save.assert_called_once()
    mock_coverage_instance.report.assert_called_once()
    mock_coverage_instance.html_report.assert_called_once_with(directory="htmlcov")
    mock_print.assert_any_call("\nTests passed successfully.", style="info")
    mock_print.assert_any_call("\nCoverage Report:", style="info")
    mock_print.assert_any_call(
        "\nDetailed HTML coverage report generated in 'htmlcov' directory.",
        style="info",
    )


@patch("starwarden.StarwardenApp.display_welcome")
@patch("starwarden.StarwardenApp.main_menu")
@patch("starwarden.StarwardenApp.select_or_create_collection")
def test_run_with_no_collection_selected(
    mock_select, mock_menu, mock_welcome, starwarden_app
):
    starwarden_app.args.id = None
    mock_menu.return_value = 1
    mock_select.return_value = None

    starwarden_app.run()

    mock_welcome.assert_called_once()
    mock_menu.assert_called_once()
    mock_select.assert_called_once()
    starwarden_app.linkwarden_manager.get_existing_links.assert_not_called()
    starwarden_app.github_manager.user.get_starred.assert_not_called()
    starwarden_app.github_manager.starred_repos.assert_not_called()
