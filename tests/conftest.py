from contextlib import suppress
from pathlib import Path

import pytest

from libraries.browser_container import BrowserContainer
from libraries.driver_factory import DriverFactory
from libraries.vnc_client import VncClient


@pytest.fixture(scope="module")
def browser(request, browser_type_and_version, worker_id, headless, record_dir):
    """Parametrized browser container (Selenium Remote Server)"""
    browser_type, browser_version = browser_type_and_version

    # Use alternative host ports incremented by the index for parallel testing with pytest-xdist.
    # This avoids host port conflicts among containers
    index = 0 if worker_id == "master" else int(worker_id[-1])

    # Run browser container
    container = BrowserContainer(
        browser_type,
        browser_version,
        index=index,
        headless=headless,
        record_dir=(record_dir or Path(request.config.rootdir, "videos")),
    ).run()

    # Connect to the VNC server (for non-headless mode)
    with VncClient(port=container.vnc_port).connect() if not headless else suppress():
        yield container
    container.delete()


@pytest.fixture
def driver(request, browser, record):
    """Selenium RemoteWebDriver"""
    driver = DriverFactory.create(
        browser.browser_type,
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
