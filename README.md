# StarWarden

StarWarden exports GitHub starred repositories to Linkwarden as individual links.

![screenshot](https://github.com/rtuszik/starwarden/blob/main/assets/screenshot.png?raw=true)

## Features

- Export GitHub stars to Linkwarden
- Create new or update existing Linkwarden collections
- Handle API rate limiting
- Command-line interface

## Requirements

- Python 3.6+
- GitHub account
- Linkwarden account and API token
- Python packages listed in `requirements.txt`

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

For debug logging:

```bash
python starwarden.py --debug
```

Follow the prompts to update or create a collection.
