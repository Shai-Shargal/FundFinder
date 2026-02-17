"""HUJI (Hebrew University) scholarship source."""

from .mapper import map_huji_json_to_grant
from .scraper import HUJIScraper

__all__ = ["map_huji_json_to_grant", "HUJIScraper"]
