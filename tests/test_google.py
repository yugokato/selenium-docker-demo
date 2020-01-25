import time

import pytest
from selenium.webdriver.common.keys import Keys


@pytest.mark.parametrize("search_word", ["cat", "dog", "rabbit", "bird"])
def test_google(driver, search_word):
    url = "https://www.google.com/"
    driver.get(url)
    assert driver.current_url == url

    q = driver.find_element_by_xpath("//input[@name='q']")
    q.send_keys(search_word)
    q.send_keys(Keys.ENTER)

    time.sleep(5)
