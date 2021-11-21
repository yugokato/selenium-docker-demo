import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.parametrize("search_word", ["cat", "dog", "rabbit", "bird"])
def test_google(driver, wait, search_word):
    url = "https://www.google.com/"
    driver.get(url)
    wait.until(EC.url_to_be(url))
    assert driver.current_url == url

    q = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='q']")))
    q.send_keys(search_word)
    q.send_keys(Keys.ENTER)

    time.sleep(5)
