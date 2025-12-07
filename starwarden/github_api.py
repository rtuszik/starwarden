import time
from math import ceil

from github import Github, GithubException, RateLimitExceededException
from urllib3 import Retry

from starwarden.utils.logger import get_logger

logger = get_logger()


def config_retry(backoff_factor=1.0, total=8):
    Retry.DEFAULT_BACKOFF_MAX = backoff_factor * 2 ** (total - 1)
    return Retry(total=total, backoff_factor=backoff_factor)


def get_starred_repos(github_token, github_username):
    gh = Github(github_token, retry=config_retry()) if github_token else Github(retry=config_retry())
    user = gh.get_user(github_username)
    starred = user.get_starred()
    total_pages = ceil(starred.totalCount / 30)

    for page_num in range(total_pages):
        while True:
            try:
                yield from starred.get_page(page_num)
                break
            except RateLimitExceededException as e:
                handle_rate_limit(e)
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    handle_rate_limit(e)
                else:
                    logger.error(f"GitHub API error: {str(e)}")
                    raise


def handle_rate_limit(e, retry_after=None):
    if retry_after is None:
        retry_after = e.headers.get("Retry-After", 60)

    retry_after = int(retry_after)
    logger.warning(f"Rate limit exceeded. Waiting for {retry_after} seconds before retrying.")
    time.sleep(retry_after)


def get_total_starred_repos(github_token, github_username):
    gh = Github(github_token, retry=config_retry()) if github_token else Github(retry=config_retry())
    user = gh.get_user(github_username)
    return user.get_starred().totalCount
