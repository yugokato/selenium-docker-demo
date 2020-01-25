import time

import pytest
from selenium.webdriver.common.keys import Keys


@pytest.mark.parametrize("search_word", ["cat", "dog", "rabbit", "bird"])
def test_yahoo(driver, search_word):
    url = "https://www.yahoo.com/"
    driver.get(url)
    assert url in driver.current_url

    q = driver.find_element_by_xpath("//input[@name='p']")
    q.send_keys(search_word)
    q.send_keys(Keys.ENTER)

    time.sleep(5)
