import re

import pytest

DEFAULT_BROWSERS = ["chrome", "firefox"]
DEFAULT_VERSIONS = ["latest"]


def pytest_addoption(parser):
    """Custom Pytest command line options"""
    parser.addoption(
        "--browser",
        dest="browsers",
        nargs="+",
        choices=DEFAULT_BROWSERS,
        default=DEFAULT_BROWSERS,
        help="Browser(s) to test with. Both Chrome and Firefox will be tested by default",
    )

    parser.addoption(
        "--chrome-version",
        dest="chrome_versions",
        metavar="CHROME_VERSION",
        nargs="*",
        help="Chrome version(s) to test with. The latest version will be tested by default",
    )
    parser.addoption(
        "--firefox-version",
        dest="firefox_versions",
        metavar="FIREFOX_VERSION",
        nargs="*",
        help="Firefox version(s) to test with. The latest version will be tested by default",
    )

    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run tests in headless mode",
    )

    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Enable video recording during tests. This option will be ignored for headless mode",
    )

    parser.addoption(
        "--record-dir", help="Directory to store video files",
    )


def pytest_keyboard_interrupt(excinfo):
    """Force teardown containers on KeyboardInterrupt"""
    cleanup_containers()


def pytest_generate_tests(metafunc):
    """Dynamically parametrize browser type and browser version pairs based on arguments passed to Pytest command

    eg. pytest --chrome-version latest 79.0.3945.117 --firefox-version 72.0.1 will generate params:
        [("chrome", "latest"), ("chrome", "79.0.3945.117"), ("firefox", "72.0.1")]
    """
    if "browser_type_and_version" in metafunc.fixturenames:
        option = metafunc.config.option
        browsers = option.browsers
        chrome_versions = option.chrome_versions or DEFAULT_VERSIONS
        firefox_versions = option.firefox_versions or DEFAULT_VERSIONS
        browser_type_and_version_pairs = []
        for browser in browsers:
            versions = chrome_versions if browser == "chrome" else firefox_versions
            browser_type_and_version_pairs.extend(
                [
                    pytest.param((browser, version), id=f"({browser}:{version})")
                    for version in versions
                    if version
                ]
            )

        metafunc.parametrize(
            "browser_type_and_version", browser_type_and_version_pairs, scope="module"
        )


@pytest.fixture(scope="session")
def headless(request):
    """Return a flag whether headless mode or not"""
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def record(request, headless):
    """Return a flag whether video recording is enabled or not

    Warning:
        Video recording uses extra CPU resources.
        Probably not a good idea to use together with xdist mode
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
    """Cleanup existing browser containers"""
    import docker

    docker_client = docker.from_env()
    containers = docker_client.containers.list(ignore_removed=True)
    for container in containers:
        try:
            image_name = container.attrs["Config"]["Image"]
            if re.match(r"^selenium-(?:chrome|firefox):", image_name):
                container.remove(force=True)
        except Exception:
            pass


# Cleanup existing browser containers
cleanup_containers()
