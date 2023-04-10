import re

import docker
import pytest
from _pytest.main import Session

from libraries.browser_container import SUPPORTED_BROWSERS


def pytest_addoption(parser):
    """Custom Pytest command line options"""
    parser.addoption(
        "--browser",
        dest="browsers",
        nargs="+",
        choices=SUPPORTED_BROWSERS,
        default=SUPPORTED_BROWSERS,
        help="Browser(s) to test with",
    )

    parser.addoption("--headless", action="store_true", default=False, help="Run tests in headless mode")

    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Enable video recording during tests. This option will be ignored for headless mode",
    )

    parser.addoption("--record-dir", help="Directory to store recorded video files")


def pytest_sessionstart(session: Session):
    cleanup_containers()


def pytest_keyboard_interrupt(excinfo):
    """Force teardown containers on KeyboardInterrupt"""
    cleanup_containers()


def pytest_generate_tests(metafunc):
    """Dynamically parametrize browser type based on arguments passed to Pytest command"""
    if "browser_type" in metafunc.fixturenames:
        option = metafunc.config.option
        browsers = option.browsers
        browser_type_and_version_pairs = []
        ids = []
        # For now, we only support the latest version in this demo. This can be expanded to support multiple versions
        version = "latest"
        for browser in browsers:
            browser_type_and_version_pairs.extend(
                [pytest.param(browser, version, marks=pytest.mark.xdist_group(f"{browser}:{version}"))]
            )
            ids.extend([f"({browser}:{version})"])

        metafunc.parametrize(
            ("browser_type", "browser_version"), browser_type_and_version_pairs, ids=ids, scope="session"
        )


@pytest.fixture(scope="session")
def headless(request):
    """Return a flag whether headless mode or not"""
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def record(request, headless):
    """Return a flag whether video recording is enabled or not

    Warning:
        Video recording uses extra CPU resources. Probably not a good idea to use together with xdist mode
    """
    record_video = request.config.getoption("--record")
    if record_video and headless:
        print("WARNING: headless mode does not support video recording")
        return False
    else:
        return record_video


@pytest.fixture(scope="session")
def record_dir(request):
    """Return a path to a directory recorded video files will be stored"""
    return request.config.getoption("--record-dir")


def cleanup_containers():
    """Clean up browser containers"""
    docker_client = docker.from_env()
    containers = docker_client.containers.list(ignore_removed=True)
    for container in containers:
        try:
            image_name = container.attrs["Config"]["Image"]
            if re.match(rf"^selenium-({'|'.join(SUPPORTED_BROWSERS)}):", image_name):
                container.remove(force=True)
        except Exception:
            pass
