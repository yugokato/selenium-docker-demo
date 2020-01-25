Quick-and-dirty Cross-browser GUI Testing in Python with Selenium and Docker
==============================================================

This repository was created to demonstrate how on-demand cross-browser GUI testing can be achieved quickly and easily in Python (Pytest) with Selenium and Docker. 

# How it works
The basic idea is simple.  
You pass desired browser types and browser versions as Pytest command line arguments. Then those values will be parametrized.  
For each parameter, the following steps will be executed.

1. Create a new browser container on-demand
2. Do test
3. Destroy the browser container  

The goal is to achieve cross-browser testing quickly and easily, therefore it doesn't require a Selenium Grid cluster, and it doesn't maintain any resources across tests. It just takes advantage of disposable resources and existing Pytest's capabilities.



# Pytest command options
```
$ pytest -h

<snip>

custom options:
  --browser={chrome,firefox} [{chrome,firefox} ...]
                        Browser(s) to test with. Both Chrome and Firefox will be tested by default
  --chrome-version=[CHROME_VERSION [CHROME_VERSION ...]]
                        Chrome version(s) to test with. The latest version will be tested by default
  --firefox-version=[FIREFOX_VERSION [FIREFOX_VERSION ...]]
                        Firefox version(s) to test with. The latest version will be tested by default
  --headless            Run tests in headless mode
  --record              Enable video recording during tests. This option will be ignored for headless mode
  --record-dir=RECORD_DIR
                        Directory to store video files
```


# Examples of usage

```bash
# Run tests with Chrome/Firefox latest versions (default)
$ pytest

# Run tests with Chrome/Firefox latest versions - headless mode
$ pytest --headless

# Run tests with Chrome/Firefox latest versions - video recording
$ pytest --record

# Run tests with Chrome latest, 79.0.3945.117 & Firefox 71.0
$ pytest --chrome-version latest 79.0.3945.117 --firefox-version 71.0

# Run tests with Chrome latest
$ pytest --browser chrome

# Run tests with Chrome 79.0.3945.130, 79.0.3945.117
$ pytest --browser chrome --chrome-version 79.0.3945.130, 79.0.3945.117

# Run tests with Firefox latest
$ pytest --browser firefox

# Run tests with Firefox 72.0, 71.0, 70.0, 69.0
$ pytest --browser firefox --firefox-version 72.0 71.0 70.0, 69.0

# Run tests in parallel using 4 CPUs with Chrome/Firefox latest versions
$ pytest --headless -n 4

# Run tests in parallel (grouped by file name) using 3 CPUs with Chrome/Firefox latest versions
$ pytest --headless -n 3 --dist=loadfile --browser chrome
```

# Sample results

##### *Sequential testing*
```bash
~/Desktop/selenium-docker-demo$ pytest -v tests/test_google.py 
=================================== test session starts ===================================
platform darwin -- Python 3.7.6, pytest-5.3.2, py-1.8.1, pluggy-0.13.1 -- /Users/yugokato/.pyenv/versions/3.7.6/envs/selenium-docker/bin/python3.7
cachedir: .pytest_cache
rootdir: /Users/yugokato/Desktop/selenium-docker-demo
plugins: xdist-1.31.0, forked-1.1.3
collected 8 items                                                                         

tests/test_google.py::test_google[(chrome:latest)-cat] PASSED                       [ 12%]
tests/test_google.py::test_google[(chrome:latest)-dog] PASSED                       [ 25%]
tests/test_google.py::test_google[(chrome:latest)-rabbit] PASSED                    [ 37%]
tests/test_google.py::test_google[(chrome:latest)-bird] PASSED                      [ 50%]
tests/test_google.py::test_google[(firefox:latest)-cat] PASSED                      [ 62%]
tests/test_google.py::test_google[(firefox:latest)-dog] PASSED                      [ 75%]
tests/test_google.py::test_google[(firefox:latest)-rabbit] PASSED                   [ 87%]
tests/test_google.py::test_google[(firefox:latest)-bird] PASSED                     [100%]

============================== 8 passed in 90.01s (0:01:30) ===============================
```

##### *Parallel testing*
```bash
~/Desktop/selenium-docker-demo$ pytest -v tests/test_google.py --headless -n 4
=================================== test session starts ===================================
platform darwin -- Python 3.7.6, pytest-5.3.3, py-1.8.1, pluggy-0.13.1 -- /Users/yugokato/.pyenv/versions/3.7.6/envs/selenium-docker-demo/bin/python3.7
cachedir: .pytest_cache
rootdir: /Users/yugokato/Desktop/selenium-docker-demo
plugins: xdist-1.31.0, forked-1.1.3
[gw0] darwin Python 3.7.6 cwd: /Users/yugokato/Desktop/selenium-docker-demo
[gw1] darwin Python 3.7.6 cwd: /Users/yugokato/Desktop/selenium-docker-demo
[gw2] darwin Python 3.7.6 cwd: /Users/yugokato/Desktop/selenium-docker-demo
[gw3] darwin Python 3.7.6 cwd: /Users/yugokato/Desktop/selenium-docker-demo
[gw0] Python 3.7.6 (default, Jan 14 2020, 12:03:26)  -- [Clang 10.0.1 (clang-1001.0.46.4)]
[gw1] Python 3.7.6 (default, Jan 14 2020, 12:03:26)  -- [Clang 10.0.1 (clang-1001.0.46.4)]
[gw2] Python 3.7.6 (default, Jan 14 2020, 12:03:26)  -- [Clang 10.0.1 (clang-1001.0.46.4)]
[gw3] Python 3.7.6 (default, Jan 14 2020, 12:03:26)  -- [Clang 10.0.1 (clang-1001.0.46.4)]
gw0 [8] / gw1 [8] / gw2 [8] / gw3 [8]
scheduling tests via LoadScheduling

tests/test_google.py::test_google[(chrome:latest)-bird] 
tests/test_google.py::test_google[(chrome:latest)-cat] 
tests/test_google.py::test_google[(chrome:latest)-rabbit] 
tests/test_google.py::test_google[(chrome:latest)-dog] 
[gw1] [ 12%] PASSED tests/test_google.py::test_google[(chrome:latest)-dog] 
[gw3] [ 25%] PASSED tests/test_google.py::test_google[(chrome:latest)-bird] 
[gw2] [ 37%] PASSED tests/test_google.py::test_google[(chrome:latest)-rabbit] 
tests/test_google.py::test_google[(firefox:latest)-dog] 
tests/test_google.py::test_google[(firefox:latest)-bird] 
tests/test_google.py::test_google[(firefox:latest)-rabbit] 
[gw0] [ 50%] PASSED tests/test_google.py::test_google[(chrome:latest)-cat] 
tests/test_google.py::test_google[(firefox:latest)-cat] 
[gw0] [ 62%] PASSED tests/test_google.py::test_google[(firefox:latest)-cat] 
[gw3] [ 75%] PASSED tests/test_google.py::test_google[(firefox:latest)-bird] 
[gw1] [ 87%] PASSED tests/test_google.py::test_google[(firefox:latest)-dog] 
[gw2] [100%] PASSED tests/test_google.py::test_google[(firefox:latest)-rabbit] 

=================================== 8 passed in 35.00s ====================================
```

# Try it out
Clone this repository and `cd` into directory,

```bash
# Install dependencies
$ pip install -r requirements

# Build images
$ ./build/build_browser_image.py

# Run tests
$ pytest -v
```

You can also specify previous versions. (eg. Chrome 76.0.3809.87 & Firefox 69.0)
```
$ ./build/build_browser_image.py --chrome-version 69.0.3497.100 --firefox-version 69.0
```

> Custom Chrome/Firefox images will be built on top of [selenium/standalone-chrome-debug](https://github.com/SeleniumHQ/docker-selenium/tree/master/StandaloneChromeDebug) and [selenium/standalone-firefox-debug](https://github.com/SeleniumHQ/docker-selenium/tree/master/StandaloneFirefoxDebug) images. 



##### *System requirements*
- *nix OS (Tested with Ubuntu 18.04 and OSX 10.14.6)
- Docker (Tested with docker-CE 19.03.5)
- Python >= 3.6 (Tested with 3.6.9, 3.7.6, and 3.8.1)
- RealVNC Viewer https://www.realvnc.com/en/connect/download/viewer/




# Write your own script
The module-scoped `driver` fixture (Instance of Selenium RemoteWebDriver) is available in your test functions. It is implicitly parametrized based on various browser types and browser versions you passed as Pytest command line arguments, or Chrome/Firefox latest versions by default. A corresponding browser container should be up and running by the time a test function is executed.  
Either use the `driver` as it is or define a custom fixture that wraps the `driver` with your own GUI automation framework.


```python
def test_open_google(driver):
    url = "https://www.google.com/"
    driver.get(url)
    assert driver.current_url == url
```


```python
# Import automation framework
from selenium_automation.framework import App

# wrap driver
@pytest.fixture(scope="module")
def app(driver):
    myapp = App(driver)
    return myapp

def test_login(app):
    logged_in = app.login("test_username", "test_password")
    assert logged_in
```