#!/usr/bin/env python3
"""Smoke tests for build"""


def test_imports():
    import starwarden  # noqa: F401
    from starwarden import config, github_api, linkwarden_api, main, tui  # noqa: F401
    from starwarden.utils import logger, notify  # noqa: F401


if __name__ == "__main__":
    test_imports()
