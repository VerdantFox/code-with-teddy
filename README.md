# code-with-teddy

My portfolio, blog, and mini-projects website, revamped for 2024

## Getting started

### Python

First, install [uv](https://github.com/astral-sh/uv) for package management. I recommend:

```bash
pipx install uv
```

Then install python environment:

```bash
# Create a virtual environment
uv venv --python=3.11 venv
source venv/bin/activate

# Install DEV dependencies
uv pip install -r requirements-dev.txt
```

Update requirements with:

```bash
./scripts/update-requirements.sh
```

### Node

First, install the latest versions of npm and node. Then install the node environment:

```bash
# Install node environment
npm install
```

To update the node packages run:

```bash
npm update
```
