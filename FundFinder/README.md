# FundFinder

FundFinder is a student-grants discovery platform that scrapes scholarship/grant sources, normalizes the data into a unified schema, and matches opportunities to users via smart search and an agent-like assistant.

See [design-PoC.md](docs/design-PoC.md) for architecture and current state.

## Setup

**Prerequisites:** Python 3.10+, and on macOS either Xcode Command Line Tools (`xcode-select --install`) or a Python from [python.org](https://www.python.org/) / Homebrew.

```bash
# Clone (if using git)
git clone https://github.com/Shai-Shargal/FundFinder.git
cd FundFinder

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Dependencies
pip install -r requirements.txt
```

## Project structure

- **Production pipeline** – `services/scraper/`: shared code (base, models, pipeline, utils) and `scrapers/` with **one folder per website**. Each scraper lives in `scrapers/<site_name>/`; add new scrapers there and register them in `scrapers/__init__.py`. Real scrapers will fetch from APIs (see docs). No CLI for production until those are added.
- **Examples** – `examples/` (at repo root, alongside `docs/`, `scripts/`, `tests/`) holds demo/educational code (example scraper, fixtures, demo CLI). Not part of the production pipeline.

## Run

**Example scraper** (for learning; uses a local HTML fixture):

```bash
# From repo root with venv activated
python examples/demo_cli/show_example_grants.py
```

## Test

```bash
pytest
```
