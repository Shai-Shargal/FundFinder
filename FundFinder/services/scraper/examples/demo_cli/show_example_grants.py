"""
Demo script for running the example scraper.
Not used in production.
"""

import sys
from pathlib import Path

# Allow importing from project root when run from examples/demo_cli/
_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from services.scraper.examples.example_government_scraper import ExampleGovernmentScraper
from services.scraper.utils import display_value

scraper = ExampleGovernmentScraper()
grants = scraper.scrape()
print(f"Found {len(grants)} grant(s)\n")
for i, g in enumerate(grants, 1):
    print(f"--- Grant {i} ---")
    for key, value in g.model_dump().items():
        print(f"  {key}: {display_value(value)}")
    print()
