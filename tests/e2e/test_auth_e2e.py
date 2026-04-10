"""
E2e tests: registration and login flow.
"""
import re

from playwright.sync_api import Page, expect

from tests.e2e.conftest import login, logout


def test_register_new_user(page: Page, live_server):
    page.goto("/auth/register")
    page.fill('[name="username"]', "newplayer_e2e")
    page.fill('[name="password"]', "strongpass99")
    page.fill('[name="password2"]', "strongpass99")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/auth/login"))
    expect(page.locator("body")).to_contain_text("prijaviti")


def test_register_duplicate_username(page: Page, live_server):
    page.goto("/auth/register")
    page.fill('[name="username"]', "player1")  # seeded in conftest
    page.fill('[name="password"]', "somepass123")
    page.fill('[name="password2"]', "somepass123")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"register"))
    expect(page.locator("body")).to_contain_text("zauzeto")


def test_register_password_mismatch(page: Page, live_server):
    page.goto("/auth/register")
    page.fill('[name="username"]', "uniqueuser_e2e")
    page.fill('[name="password"]', "pass1111")
    page.fill('[name="password2"]', "pass2222")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    # WTForms EqualTo keeps us on register with a form error
    expect(page).to_have_url(re.compile(r"register"))
    expect(page.locator("form")).to_be_visible()


def test_login_valid_credentials(page: Page, live_server):
    logout(page)
    login(page, "player1", "player123")

    expect(page).not_to_have_url(re.compile(r"login"))
    expect(page.locator("body")).to_contain_text("player1")


def test_login_wrong_password(page: Page, live_server):
    logout(page)
    page.goto("/auth/login")
    page.fill('[name="username"]', "player1")
    page.fill('[name="password"]', "wrongpassword")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"login"))
    expect(page.locator("body")).to_contain_text("Pogrešno")


def test_login_unknown_user(page: Page, live_server):
    page.goto("/auth/login")
    page.fill('[name="username"]', "ghost_user_xyz")
    page.fill('[name="password"]', "anything123")
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"login"))
    expect(page.locator("body")).to_contain_text("Pogrešno")


def test_logout_redirects_to_login_on_protected_page(page: Page, live_server):
    login(page, "player1", "player123")
    page.goto("/auth/logout")
    page.wait_for_load_state("networkidle")

    page.goto("/my-predictions")
    expect(page).to_have_url(re.compile(r"login"))


def test_protected_page_redirects_unauthenticated(page: Page, live_server):
    logout(page)
    page.goto("/my-predictions")
    expect(page).to_have_url(re.compile(r"login"))
