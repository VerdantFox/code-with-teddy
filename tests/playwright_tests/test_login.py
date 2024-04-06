"""test_login: test around the login/registration functionality."""

from playwright.sync_api import Page, expect

from tests.playwright_tests.conftest import UIDetails


def test_login_by_modal(page: Page, ui_details: UIDetails):
    """Test the login modal."""
    url = f"{ui_details.url}/blog"
    page.goto(url)

    page.get_by_label("User details").click()

    # Check the "Why login?" modal tippy popup.
    expect(page.locator("text='Why login?'")).not_to_be_visible()
    page.get_by_role("menu").get_by_role("button").hover()
    expect(page.locator("text='Why login?'")).to_be_visible()

    # Login modal not visible.
    expect(page.get_by_text("Sign In Username or Email")).not_to_be_visible()

    # Open the login modal.
    page.get_by_role("menuitem", name="Sign In").click()

    # Login modal is visible + sign in
    expect(page.get_by_text("Sign In Username or Email")).to_be_visible()
    page.get_by_placeholder("awesome@email.com").fill(ui_details.basic_username)
    page.get_by_label("Password").fill(ui_details.basic_password)
    page.get_by_role("button", name="Log in").click()

    # Sign in toast notification is visible
    expect(page.locator("div").filter(has_text="You are logged in!").nth(1)).to_be_visible()

    # Check that the user remains on the  blog page
    expect(page.get_by_role("heading", name="Code Chronicles")).to_be_visible()

    # Check the user menu items
    expect(page.get_by_label("User details")).to_be_visible()
    page.get_by_label("User details").click()

    # Standard user menu items are visible
    expect(page.get_by_text(f"Welcome {ui_details.basic_username}")).to_be_visible()
    expect(page.get_by_role("menuitem", name="User Settings")).to_be_visible()
    expect(page.get_by_role("menuitem", name="Sign Out")).to_be_visible()

    # Admin user menu items not visible
    expect(page.get_by_role("menuitem", name="Create Blog Post")).not_to_be_visible()

    # Sign out
    page.get_by_role("menuitem", name="Sign Out").click()
    expect(page.locator("div").filter(has_text="You are logged out!").nth(1)).to_be_visible()

    # Check that the user is actually signed out
    page.get_by_label("User details").click()
    expect(page.locator("text='Why login?'")).not_to_be_visible()

    # Check that the user stays on the same page after signing out
    expect(page.get_by_role("heading", name="Code Chronicles")).to_be_visible()


def test_login_modal_navigation(page: Page, ui_details: UIDetails):
    """Test the login modal navigation."""
    url = f"{ui_details.url}/blog"
    page.goto(url)

    # Open the login modal.
    page.get_by_label("User details").click()
    page.get_by_role("menuitem", name="Sign In").click()
    expect(page.get_by_text("Sign In Username or Email")).to_be_visible()

    # Tab through the login modal, should stay in login modal
    page.get_by_role("button").first.press("Tab")
    expect(page.get_by_label("Username or Email")).to_be_focused()

    page.get_by_label("Username or Email").press("Tab")
    expect(page.get_by_label("Password")).to_be_focused()

    page.get_by_label("Password").press("Tab")
    expect(page.get_by_role("button", name="Log in")).to_be_focused()

    page.get_by_role("button", name="Log in").press("Tab")
    expect(page.get_by_role("link", name="Register here...")).to_be_focused()

    page.get_by_role("link", name="Register here...").press("Tab")
    expect(page.get_by_role("button").first).to_be_visible()

    # Close the login modal by clicking the exit button
    page.get_by_role("button").first.press("Enter")
    expect(page.get_by_text("Sign In Username or Email")).not_to_be_visible()

    # Open the login modal again
    page.get_by_label("User details").click()
    page.get_by_role("menuitem", name="Sign In").click()

    # Close the login modal by clicking outside the modal
    page.get_by_text("Sign In Username or Email").click(position={"x": -25, "y": -25}, force=True)
    expect(page.get_by_text("Sign In Username or Email")).not_to_be_visible()
