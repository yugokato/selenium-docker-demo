from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from .browser_container import CONTAINER_WINDOW_WIDTH, CONTAINER_WINDOW_HEIGHT


SUPPORTED_BROWSERS = ["chrome", "firefox"]


class DriverFactory(object):
    """Class to create a remote WebDriver object for chrome and firefox"""

    @staticmethod
    def create(
        browser_type,
        remote_selenium_server_ip="127.0.0.1",
        remote_selenium_server_port=4444,
        headless=False,
    ):
        """Get a Selenium WebDriver object for the browser container. It retries until the browser
           container becomes ready after being spun up

        Arguments:
            browser_type (str): Browser type (chrome/firefox)
            remote_selenium_server_ip (str): Remote WebDriver Server IP address
            remote_selenium_server_ip (int): Remote WebDriver Server port
            headless (bool): Headless mode

        Returns:
            WebDriver: Remote WebDriver object
        """
        if browser_type not in SUPPORTED_BROWSERS:
            raise Exception(f"{browser_type} is not supported")

        # Create driver
        driver = DriverFactory.__init_driver(
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
    def __init_driver(
        browser_type,
        remote_selenium_server_ip,
        remote_selenium_server_port,
        headless=False,
    ):
        command_executor = (
            f"http://{remote_selenium_server_ip}:{remote_selenium_server_port}/wd/hub"
        )

        # Google Chrome
        if browser_type == "chrome":
            capabilities = DesiredCapabilities.CHROME.copy()
            chrome_options = ChromeOptions()
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)
            if headless:
                chrome_options.add_argument("--headless")
                chrome_options.add_argument(
                    f"--window-size={CONTAINER_WINDOW_WIDTH}x{CONTAINER_WINDOW_HEIGHT}"
                )
            params = dict(
                command_executor=command_executor,
                desired_capabilities=capabilities,
                options=chrome_options,
            )
        # Mozilla Firefox
        else:
            capabilities = DesiredCapabilities.FIREFOX.copy()
            firefox_profile = webdriver.FirefoxProfile()
            firefox_options = FirefoxOptions()
            # Suppress popups or user's confirmation when downloading files (Add more if you need)
            prefs = (
                "text/csv,application/x-msexcel,application/excel,"
                "application/x-excel,application/vnd.ms-excel,"
                "image/png,image/jpeg,text/html,text/plain,"
                "application/msword,application/xml,"
            )
            firefox_profile.set_preference("browser.download.folderList", 1)
            firefox_profile.set_preference(
                "browser.helperApps.neverAsk.openFile", prefs
            )
            firefox_profile.set_preference(
                "browser.helperApps.neverAsk.saveToDisk", prefs
            )
            firefox_profile.update_preferences()
            firefox_options.profile = firefox_profile
            if headless:
                firefox_options.add_argument("--headless")
            params = dict(
                command_executor=command_executor,
                desired_capabilities=capabilities,
                options=firefox_options,
            )

        driver = webdriver.Remote(**params)
        return driver
