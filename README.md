![Docker Pulls](https://img.shields.io/docker/pulls/rtuszik/starwarden) ![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/rtuszik/starwarden/docker.yml) ![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/rtuszik/starwarden/lint.yml)

# StarWarden

StarWarden allows you to export GitHub stars to Linkwarden.

![screenshot](https://github.com/rtuszik/starwarden/blob/main/assets/screenshot.png?raw=true)

## Features

- Export GitHub stars to Linkwarden
- Export to existing collection or create new colletion
- Keep Linkwarden collection up-to-date with your GitHub stars using the docker image.

## Setup

Uses [astral/uv](https://docs.astral.sh/uv/getting-started/installation/)

Install:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Clone the repository
2. Install requirements:

    ```bash
    uv sync --locked
    ```

3. Create a `.env` file with:

    ```bash
    GITHUB_TOKEN=your_github_token
    GITHUB_USERNAME=your_github_username
    LINKWARDEN_URL=your_linkwarden_instance_url
    LINKWARDEN_TOKEN=your_linkwarden_api_token
    APPRISE_URLS=apprise_url_1,apprise_url_2
    OPT_TAG=true
    OPT_TAG_GITHUB=true
    OPT_TAG_GITHUBSTARS=true
    OPT_TAG_LANGUAGE=false
    OPT_TAG_USERNAME=false
    ```

## Usage

Run:

```bash
uv run starwarden.py
```

To directly update an existing collection without an interactive menu, run:

```bash
uv run starwarden.py -id YOUR_COLLECTION_ID
```

## Environment Variables

| Name                |   Default    | Description                                                                                                    |
| :------------------ | :----------: | :------------------------------------------------------------------------------------------------------------- |
| GITHUB_TOKEN        |              | GitHub API token                                                                                               |
| GITHUB_USERNAME     |              | GitHub username                                                                                                |
| LINKWARDEN_URL      |              | Linkwarden URL https://your-linkwarden-instance.com                                                            |
| LINKWARDEN_TOKEN    |              | Linkwarden API token                                                                                           |
| COLLECTION_ID       |              | Linkwarden Collection ID to update (Number) /collections/499                                                   |
| CRON_SCHEDULE       | 0 6 \* \* \* | Cron Schedule (default is daily at 6am)                                                                        |
| APPRISE_URLS        |              | Apprise URL for push notifications, separated by commas, see [Apprise](https://github.com/caronc/apprise/wiki) |
| OPT_TAG             |     true     | Enable/Disable all Tagging                                                                                     |
| OPT_TAG_GITHUB      |     true     | Tag Link with "GitHub"                                                                                         |
| OPT_TAG_GITHUBSTARS |     true     | Tag Link with "GitHub Stars"                                                                                   |
| OPT_TAG_LANGUAGE    |    false     | Tag Link with Language of repo (e.g. Python or JavaScript)                                                     |
| OPT_TAG_USERNAME    |    false     | Tag GitHub username                                                                                            |
| OPT_TAG_CUSTOM      |              | Add custom tags, separated by commas (e.g. tag1,tag2)                                                          |

## Unsupervised Updates

For automated, unsupervised updates, you can use Docker with the provided docker-compose.yml file.

1. Make sure you have Docker and Docker Compose installed on your system.

2. Create a `.env` file in the project root with the following variables:

    ```bash
    GITHUB_TOKEN=your_github_token
    GITHUB_USERNAME=your_github_username
    LINKWARDEN_URL=your_linkwarden_instance_url
    LINKWARDEN_TOKEN=your_linkwarden_api_token
    COLLECTION_ID=your_linkwarden_collection_id
    CRON_SCHEDULE=0 0 * * *  # Run daily at midnight, adjust as needed
    APPRISE_URLS=apprise_url_1,apprise_url_2
    OPT_TAG=true
    OPT_TAG_GITHUB=true
    OPT_TAG_GITHUBSTARS=true
    OPT_TAG_LANGUAGE=false
    OPT_TAG_USERNAME=false
    ```

3. Use the following `docker-compose.yml` file:

    ```yaml
    version: "3"
    services:
    starwarden:
        image: rtuszik/starwarden:latest
        env_file: .env
        volumes:
            - ./starwarden.log:/app/starwarden.log
    ```

4. Run the following command to start the Docker container:

    ```bash
    docker compose up -d
    ```

The container will now automatically run StarWarden on the specified schedule without any manual intervention.

To manually trigger an update, you can run:

```bash
docker compose exec starwarden python /app/starwarden.py -id $COLLECTION_ID
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
