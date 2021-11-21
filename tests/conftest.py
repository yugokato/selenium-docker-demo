from contextlib import suppress

import pytest
from _pytest.fixtures import FixtureRequest
from selenium.webdriver.support.ui import WebDriverWait

from libraries.browser_container import BrowserContainer
from libraries.driver_factory import DriverFactory


@pytest.fixture(scope="session")
def browser(browser_type, browser_version, headless, record_dir):
    """Parametrized browser container (Selenium Remote Server)"""

    container = BrowserContainer(browser_type, browser_version, headless=headless, record_dir=record_dir).run()
    if not headless:
        container.open_browser(view_only=True)
    yield container
    container.delete()


@pytest.fixture
def driver(request: FixtureRequest, browser, record):
    """Selenium RemoteWebDriver"""
    driver = DriverFactory.create(
        browser.browser_type,
        remote_selenium_server_ip=browser.selenium_server,
        remote_selenium_server_port=browser.selenium_port,
        headless=browser.headless,
    )

    # Record video if video recording is enabled
    filename = f"{request.node.name}.mp4"
    with browser.record_video(filename) if record else suppress():
        yield driver
    try:
        driver.quit()
    except Exception:
        # Ignore any exceptions in case the container has been already deleted
        pass


@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 30)
