Quick-and-dirty Cross-browser GUI Testing in Python with Selenium and Docker
==============================================================

This repository was created to demonstrate how on-demand cross-browser GUI testing can be achieved quickly and easily in Python (Pytest) using [docker-selenium](https://github.com/SeleniumHQ/docker-selenium)  images

# How it works
The basic idea is simple.  
You pass desired browser types as Pytest command line arguments. Then those values will be parametrized.  
For each parameter (browser), the following steps will be executed.

1. Create a new browser container on-demand
2. Run tests
3. Destroy the browser container  

The goal is to achieve cross-browser testing quickly and easily, therefore it doesn't require a typical Selenium Grid cluster setup, and it doesn't maintain any resources across tests. It just takes advantage of disposable resources and existing Pytest's capabilities.


# Try it out
Clone this repository and `cd` into directory,

```bash
# Install dependencies
$ pip install -r requirements.txt

# Build images (chrome/firefox/edge). This will take some time for the first run
$ ./scripts/build_browser_image.py

# Run tests
$ pytest -v
```

##### *System requirements*
- *nix OS
- Docker (Tested with version 20.10.6, build 370c289)
- Python >= 3.8 (Tested with 3.8.9 and 3.9.8)


# Pytest command options
```
$ pytest -h

<snip>

custom options:
  --browser={chrome,firefox,edge} [{chrome,firefox,edge} ...]
                        Browser(s) to test with
  --headless            Run tests in headless mode
  --record              Enable video recording during tests. This option will be ignored for headless mode
  --record-dir=RECORD_DIR
                        Directory to store recorded video files
```


# Examples of usage

```sh
# Run tests with all browsers
$ pytest [PYTEST_OPTIONS]

# Run tests with all browsers in parallel using pytest-xdist
$ pytest [PYTEST_OPTIONS] -n 3

# Run tests with a specific browser
$ pytest [PYTEST_OPTIONS] --browser chrome

# Run tests with specific browsers
$ pytest [PYTEST_OPTIONS] --browser chrome firefox

# Run tests in headless mode
$ pytest [PYTEST_OPTIONS] --browser chrome --headless

# Record video
$ pytest [PYTEST_OPTIONS] --browser chrome --record
```
> Unless `--headless` option is explicitly provided, the test session will automatically open your default browser and show the browser container's screen using [noVNC](https://github.com/novnc/noVNC)


# Sample results

##### *Sequential testing*
```bash
~/Desktop/selenium-docker-demo$ pytest -v tests/test_google.py
================================== test session starts ===================================
platform darwin -- Python 3.9.8, pytest-6.2.5, py-1.11.0, pluggy-1.0.0 -- /Users/yugo/.pyenv/versions/3.9.8/envs/selenium-docker-demo-3.9.8/bin/python3.9
cachedir: .pytest_cache
rootdir: /Users/yugo/Desktop/selenium-docker-demo
plugins: xdist-2.4.0, forked-1.3.0
collected 12 items                                                                       

tests/test_google.py::test_google[(chrome:latest)-cat] PASSED                      [  8%]
tests/test_google.py::test_google[(chrome:latest)-dog] PASSED                      [ 16%]
tests/test_google.py::test_google[(chrome:latest)-rabbit] PASSED                   [ 25%]
tests/test_google.py::test_google[(chrome:latest)-bird] PASSED                     [ 33%]
tests/test_google.py::test_google[(firefox:latest)-cat] PASSED                     [ 41%]
tests/test_google.py::test_google[(firefox:latest)-dog] PASSED                     [ 50%]
tests/test_google.py::test_google[(firefox:latest)-rabbit] PASSED                  [ 58%]
tests/test_google.py::test_google[(firefox:latest)-bird] PASSED                    [ 66%]
tests/test_google.py::test_google[(edge:latest)-cat] PASSED                        [ 75%]
tests/test_google.py::test_google[(edge:latest)-dog] PASSED                        [ 83%]
tests/test_google.py::test_google[(edge:latest)-rabbit] PASSED                     [ 91%]
tests/test_google.py::test_google[(edge:latest)-bird] PASSED                       [100%]

============================= 12 passed in 189.63s (0:03:09) =============================
```

##### *Parallel testing*
```bash
~/Desktop/selenium-docker-demo$ pytest -v tests/test_google.py --headless -n 3
================================== test session starts ===================================
platform darwin -- Python 3.9.8, pytest-6.2.5, py-1.11.0, pluggy-1.0.0 -- /Users/yugo/.pyenv/versions/3.9.8/envs/selenium-docker-demo-3.9.8/bin/python3.9
cachedir: .pytest_cache
rootdir: /Users/yugo/Desktop/selenium-docker-demo
plugins: xdist-2.4.0, forked-1.3.0
[gw0] darwin Python 3.9.8 cwd: /Users/yugo/Desktop/selenium-docker-demo
[gw1] darwin Python 3.9.8 cwd: /Users/yugo/Desktop/selenium-docker-demo
[gw2] darwin Python 3.9.8 cwd: /Users/yugo/Desktop/selenium-docker-demo
[gw0] Python 3.9.8 (main, Nov 11 2021, 19:58:26)  -- [Clang 12.0.0 (clang-1200.0.32.29)]
[gw1] Python 3.9.8 (main, Nov 11 2021, 19:58:26)  -- [Clang 12.0.0 (clang-1200.0.32.29)]
[gw2] Python 3.9.8 (main, Nov 11 2021, 19:58:26)  -- [Clang 12.0.0 (clang-1200.0.32.29)]
gw0 [12] / gw1 [12] / gw2 [12]
scheduling tests via LoadBrowserScheduling

tests/test_google.py::test_google[(edge:latest)-cat] 
tests/test_google.py::test_google[(chrome:latest)-cat] 
tests/test_google.py::test_google[(firefox:latest)-cat] 
[gw0] [  8%] PASSED tests/test_google.py::test_google[(chrome:latest)-cat] 
tests/test_google.py::test_google[(chrome:latest)-dog] 
[gw2] [ 16%] PASSED tests/test_google.py::test_google[(edge:latest)-cat] 
tests/test_google.py::test_google[(edge:latest)-dog] 
[gw1] [ 25%] PASSED tests/test_google.py::test_google[(firefox:latest)-cat] 
tests/test_google.py::test_google[(firefox:latest)-dog] 
[gw0] [ 33%] PASSED tests/test_google.py::test_google[(chrome:latest)-dog] 
tests/test_google.py::test_google[(chrome:latest)-rabbit] 
[gw2] [ 41%] PASSED tests/test_google.py::test_google[(edge:latest)-dog] 
tests/test_google.py::test_google[(edge:latest)-rabbit] 
[gw1] [ 50%] PASSED tests/test_google.py::test_google[(firefox:latest)-dog] 
tests/test_google.py::test_google[(firefox:latest)-rabbit] 
[gw0] [ 58%] PASSED tests/test_google.py::test_google[(chrome:latest)-rabbit] 
tests/test_google.py::test_google[(chrome:latest)-bird] 
[gw2] [ 66%] PASSED tests/test_google.py::test_google[(edge:latest)-rabbit] 
tests/test_google.py::test_google[(edge:latest)-bird] 
[gw1] [ 75%] PASSED tests/test_google.py::test_google[(firefox:latest)-rabbit] 
tests/test_google.py::test_google[(firefox:latest)-bird] 
[gw0] [ 83%] PASSED tests/test_google.py::test_google[(chrome:latest)-bird] 
[gw2] [ 91%] PASSED tests/test_google.py::test_google[(edge:latest)-bird] 
[gw1] [100%] PASSED tests/test_google.py::test_google[(firefox:latest)-bird] 

============================= 12 passed in 74.31s (0:01:14) ==============================
```

In this scenario 3 containers will run at the same time
```sh
~/Desktop/selenium-docker-demo$ docker ps
CONTAINER ID   IMAGE                     COMMAND                  CREATED          STATUS          PORTS                                                                                            NAMES
0fd80386b873   selenium-firefox:latest   "/opt/bin/entry_poin…"   41 seconds ago   Up 34 seconds   5900/tcp, 0.0.0.0:4445->4444/tcp, :::4445->4444/tcp, 0.0.0.0:7901->7900/tcp, :::7901->7900/tcp   goofy_turing
f5eb3340bad4   selenium-chrome:latest    "/opt/bin/entry_poin…"   41 seconds ago   Up 35 seconds   0.0.0.0:4444->4444/tcp, :::4444->4444/tcp, 0.0.0.0:7900->7900/tcp, :::7900->7900/tcp, 5900/tcp   romantic_thompson
c50270a802b1   selenium-edge:latest      "/opt/bin/entry_poin…"   41 seconds ago   Up 36 seconds   5900/tcp, 0.0.0.0:4446->4444/tcp, :::4446->4444/tcp, 0.0.0.0:7902->7900/tcp, :::7902->7900/tcp   vibrant_swartz
```

# Write your own script
The `driver` fixture (an instance of Selenium RemoteWebDriver) is available in your test functions. It is implicitly 
parametrized based on browser types you passed as Pytest command line arguments, or 
Chrome/Firefox/Edge by default. A corresponding browser container should be up and running by the time 
a test function is executed.  
Either use the `driver` as it is or define a custom fixture that wraps the `driver` with your own GUI automation framework.

conftest.py
```python
import pytest

# Import your Selenium automation framework
from selenium_automation.framework import App   # noqa

@pytest.fixture
def app(driver):
    """My application"""
    myapp = App(driver)
    myapp.login()
    yield myapp
    myapp.logout()
```

test.py
```python
def test_do_something(app):
    result = app.do_something()
    assert result
```