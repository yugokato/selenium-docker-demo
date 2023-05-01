from selenium import webdriver
from selenium.webdriver import ChromeOptions, EdgeOptions, FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from libraries.browser_container import CONTAINER_WINDOW_HEIGHT, CONTAINER_WINDOW_WIDTH, SUPPORTED_BROWSERS


class DriverFactory(object):
    """Class to create a remote WebDriver object for various browsers"""

    @staticmethod
    def create(
        browser_type: str,
        remote_selenium_server_ip: str = "127.0.0.1",
        remote_selenium_server_port: int = 4444,
        headless: bool = False,
    ) -> WebDriver:
        """Get a Selenium WebDriver object for the browser container. It retries until the browser
           container becomes ready after being spun up

        :param browser_type: Browser type (chrome/firefox/edge)
        :param remote_selenium_server_ip: Remote WebDriver Server IP address
        :param remote_selenium_server_port: Remote WebDriver Server port
        :param headless: Headless mode
        """
        if browser_type not in SUPPORTED_BROWSERS:
            raise Exception(f"{browser_type} is not supported")

        # Create driver
        driver = DriverFactory._init_driver(
            browser_type,
            remote_selenium_server_ip,
            remote_selenium_server_port,
            headless=headless,
        )
        driver.delete_all_cookies()
        driver.maximize_window()
        driver.set_page_load_timeout(120)

        return driver

    @staticmethod
    def _init_driver(
        browser_type: str, remote_selenium_server_ip: str, remote_selenium_server_port: int, headless: bool = False
    ) -> WebDriver:
        command_executor = f"http://{remote_selenium_server_ip}:{remote_selenium_server_port}"

        if browser_type in ["chrome", "edge"]:
            if browser_type == "chrome":
                options = ChromeOptions()
            else:
                options = EdgeOptions()
                options.use_chromium = True
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            }
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            if headless:
                options.add_argument("--headless=new")
                options.add_argument(f"--window-size={CONTAINER_WINDOW_WIDTH}x{CONTAINER_WINDOW_HEIGHT}")
        elif browser_type == "firefox":
            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
        else:
            raise NotImplementedError(f"Unsupported browser: {browser_type}")

        options.set_capability("platformName", "Linux")

        driver = webdriver.Remote(command_executor=command_executor, options=options)
        return driver
