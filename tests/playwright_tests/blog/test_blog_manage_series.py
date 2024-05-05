"""test_blog_manage_series: test managing a blog series."""

from playwright.sync_api import Page, expect

from tests.playwright_tests import UIDetails, helpers


def test_manage_series_crud(login_admin_session_page: Page, ui_details: UIDetails) -> None:
    """Test CRUD operations for blog post series management."""
    page = login_admin_session_page
    page.wait_for_timeout(500)
    url = f"{ui_details.url}/blog/series"
    helpers.goto(page, url)

    # Create a new series
    og_name = "playwright series name"
    og_description = "playwright series description"
    add_series_locator = page.locator("#add-series")
    add_series_locator.locator("#name").fill(og_name)
    add_series_locator.locator("#description").fill(og_description)
    add_series_locator.locator("#add-series-submit-btn").click()
    # Created series in toast notification is visible
    expect(page.locator("div").filter(has_text="Series Created!").nth(1)).to_be_visible()
    page.wait_for_timeout(500)
    created_series = page.locator(".series").last
    series_name_input = created_series.locator(".series-name")
    series_description_input = created_series.locator(".series-description")
    assert series_name_input.input_value() == og_name
    assert series_description_input.input_value() == og_description

    # Update series
    updated_name = "updated playwright series name"
    updated_description = "updated playwright series description"
    series_name_input.fill(updated_name)
    series_description_input.fill(updated_description)
    created_series.locator(".update-series-btn").click()
    # Updated series in toast notification is visible
    expect(page.locator("div").filter(has_text="Series Updated!").nth(1)).to_be_visible()
    page.wait_for_timeout(500)
    assert series_name_input.input_value() == updated_name
    assert series_description_input.input_value() == updated_description

    # Delete series
    created_series.locator(".delete-series-btn").click()
    page.get_by_role("button", name="Delete").click()  # Confirm delete popup
    # Deleted series in toast notification is visible
    expect(page.locator("div").filter(has_text="Series Deleted!").nth(1)).to_be_visible()
