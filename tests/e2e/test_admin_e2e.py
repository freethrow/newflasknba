"""
E2e tests: admin creates series, closes it, player predicts, admin sets result + recalculates.

Test order matters — they share session-scoped server state (same SQLite file).
The series created in test_admin_creates_series is used by later tests.
"""
import re

from playwright.sync_api import Page, expect

from tests.e2e.conftest import login, logout


# ── helpers ──────────────────────────────────────────────────────────────────

def admin_login(page: Page):
    login(page, "admin", "admin123")


def player_login(page: Page):
    login(page, "player1", "player123")


def get_series_row(page: Page, home_team: str):
    """Return the <tr> for the given home team in the admin dashboard."""
    return page.locator(f"tr:has-text('{home_team}')")


# ── tests ─────────────────────────────────────────────────────────────────────

def test_admin_can_access_dashboard(page: Page, live_server):
    admin_login(page)
    page.goto("/admin/")
    expect(page.locator("h1")).to_contain_text("Admin panel")


def test_non_admin_blocked_from_admin(page: Page, live_server):
    logout(page)
    player_login(page)
    page.goto("/admin/")
    assert "403" in page.content() or page.status == 403


def test_admin_creates_series(page: Page, live_server):
    logout(page)
    admin_login(page)

    page.goto("/admin/series/new")
    expect(page.locator("h1")).to_contain_text("Nova serija")

    page.fill('[name="home"]', "Boston Celtics")
    page.fill('[name="away"]', "Miami Heat")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/admin/"))
    expect(page.locator("body")).to_contain_text("Boston Celtics")
    expect(page.locator("body")).to_contain_text("Miami Heat")


def test_player_can_submit_prediction(page: Page, live_server):
    """Player sees the open series on /series and submits a prediction."""
    logout(page)
    player_login(page)

    page.goto("/series")
    expect(page.locator("body")).to_contain_text("Boston Celtics")

    # Series cards have a "Detalji" link to the detail page
    page.get_by_role("link", name="Detalji").first.click()
    page.wait_for_load_state("networkidle")

    page.select_option('[name="predicted"]', "4:2")
    page.locator("#prediction-section").get_by_role("button").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("#prediction-section")).to_contain_text("4:2")


def test_admin_closes_series(page: Page, live_server):
    """Admin changes the series from Otvorena to Zatvorena via inline select."""
    logout(page)
    admin_login(page)
    page.goto("/admin/")

    series_row = get_series_row(page, "Boston Celtics")
    series_row.locator('select[name="open"]').select_option("false")
    series_row.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle")

    updated_row = get_series_row(page, "Boston Celtics")
    expect(updated_row.locator('select[name="open"]')).to_have_value("false")


def test_admin_sets_result(page: Page, live_server):
    """Admin fills in the result for the series."""
    logout(page)
    admin_login(page)
    page.goto("/admin/")

    series_row = get_series_row(page, "Boston Celtics")
    series_row.locator('input[name="result"]').fill("4:2")
    series_row.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle")

    updated_row = get_series_row(page, "Boston Celtics")
    expect(updated_row.locator('input[name="result"]')).to_have_value("4:2")


def test_admin_recalculates_scores(page: Page, live_server):
    """Admin goes to per-series predictions page and recalculates."""
    logout(page)
    admin_login(page)
    page.goto("/admin/")

    series_row = get_series_row(page, "Boston Celtics")
    series_row.get_by_role("link", name="Predikcije").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("h1")).to_contain_text("Boston Celtics")

    page.get_by_role("button", name="Ponovo izračunaj poene").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("body")).to_contain_text("Poeni")


def test_admin_can_edit_prediction_inline(page: Page, live_server):
    """Admin changes player1's prediction from the series predictions page."""
    logout(page)
    admin_login(page)
    page.goto("/admin/")

    series_row = get_series_row(page, "Boston Celtics")
    series_row.get_by_role("link", name="Predikcije").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("body")).to_contain_text("player1")

    player_row = page.locator("tr:has-text('player1')")
    predicted_select = player_row.locator('select[name="predicted"]')

    if predicted_select.count() > 0:
        predicted_select.select_option("4:3")
        player_row.locator('button[type="submit"]').click()
        page.wait_for_load_state("networkidle")
        expect(page.locator("tr:has-text('player1')")).to_contain_text("4:3")
