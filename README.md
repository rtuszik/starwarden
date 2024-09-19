# StarWarden

StarWarden exports GitHub starred repositories to Linkwarden as individual links.

![screenshot](https://github.com/rtuszik/starwarden/blob/main/assets/screenshot.png?raw=true)

## Features

- Export GitHub stars to Linkwarden
- Create new or update existing Linkwarden collections
- TUI Interface
- Docker support for unsupervised updates

## Setup

1. Clone the repository
2. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with:

   ```bash
   GITHUB_TOKEN=your_github_token
   GITHUB_USERNAME=your_github_username
   LINKWARDEN_URL=your_linkwarden_instance_url
   LINKWARDEN_TOKEN=your_linkwarden_api_token
   ```

## Usage

Run:

```bash
python starwarden.py
```

To directly update an existing collection without an interactive menu, run:

```bash
python starwarden.py -id YOUR_COLLECTION_ID
```

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
   ```

3. Use the following `docker-compose.yml` file:

   ```yaml
   version: '3'
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