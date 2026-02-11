import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Fix Windows console Unicode (cp1252 can't encode Hebrew)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from services.scraper.pipeline import get_all_scrapers, run_sources
from services.scraper.utils import display_value

grants = run_sources(get_all_scrapers())
print(f"Found {len(grants)} grant(s)\n")
for i, g in enumerate(grants, 1):
    print(f"--- Grant {i} ---")
    for key, value in g.model_dump().items():
        print(f"  {key}: {display_value(value)}")
    print()
