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

## Run

```bash
# From repo root with venv activated
python scripts/show_grants.py
```

## Test

```bash
pytest
```
