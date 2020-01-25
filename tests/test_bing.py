import time

import pytest
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


@pytest.mark.parametrize("search_word", ["cat", "dog", "rabbit", "bird"])
def test_bing(driver, search_word):
    url = "https://www.bing.com/"
    driver.get(url)
    assert driver.current_url == url

    q = driver.find_element_by_xpath("//input[@name='q']")
    if driver.name == "chrome":
        # Use ActionChains since send_keys() doesn't always work with current Chrome version in bing.com
        ActionChains(driver).send_keys_to_element(q, search_word).send_keys(
            Keys.ENTER
        ).perform()
    else:
        q.send_keys(search_word)
        q.send_keys(Keys.ENTER)

    time.sleep(5)
