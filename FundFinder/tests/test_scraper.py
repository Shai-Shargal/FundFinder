def test_run_sources_returns_grants_with_expected_title_and_content_hash():
    from services.scraper.pipeline import get_all_scrapers, run_sources

    grants = run_sources(get_all_scrapers())
    assert len(grants) >= 1
    g = grants[0]
    assert g.title == "דוגמה מלגה"
    assert g.content_hash
    assert len(g.content_hash) > 0
