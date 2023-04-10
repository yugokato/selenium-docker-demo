import atexit
import os
import re
import signal
import time
import webbrowser
from contextlib import contextmanager
from pathlib import Path
from threading import current_thread, main_thread
from typing import Optional

import docker
import docker.errors
import requests
from docker.models.containers import Container

SUPPORTED_BROWSERS = ["chrome", "firefox", "edge"]
DEFAULT_SELENIUM_SERVER = "localhost"
DEFAULT_SELENIUM_PORT = 4444
DEFAULT_NOVNC_PORT = 7900
CONTAINER_VIDEO_DIR = "/tmp/screencast"
CONTAINER_WINDOW_WIDTH = "1360"
CONTAINER_WINDOW_HEIGHT = "1020"


class BrowserContainer(object):
    """Browser container class"""

    def __init__(
        self,
        browser_type: str,
        browser_version: str = "latest",
        headless: bool = False,
        record_dir: str = None,
    ):
        if browser_type not in SUPPORTED_BROWSERS:
            raise NotImplementedError
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except docker.errors.DockerException:
            err = "ERROR: Unable to connect to the Docker daemon. Is the docker daemon running on this host?"
            raise RuntimeError(err)
        self.browser_type = browser_type
        self.browser_version = browser_version
        self.headless = headless
        self.record_dir = record_dir
        self.selenium_server = DEFAULT_SELENIUM_SERVER
        self.selenium_port = self._adjust_port(DEFAULT_SELENIUM_PORT)
        self.novnc_port = self._adjust_port(DEFAULT_NOVNC_PORT)
        self.image = f"selenium-{self.browser_type}:{self.browser_version}"
        self.__container: Optional[Container] = None

        if record_dir is None:
            self.record_dir = str(Path(__file__).parents[1] / "videos")
        Path(self.record_dir).mkdir(exist_ok=True)

    def run(self):
        """Run browser container"""
        params = dict(
            image=self.image,
            ports={f"{DEFAULT_SELENIUM_PORT}/tcp": self.selenium_port, f"{DEFAULT_NOVNC_PORT}/tcp": self.novnc_port},
            volumes={self.record_dir: {"bind": CONTAINER_VIDEO_DIR, "mode": "rw"}},
            detach=True,
            remove=True,
            shm_size="2g",
            environment={"VNC_NO_PASSWORD": "1"},
        )
        if self.headless:
            # Disable Xvfb
            params["environment"].update({"START_XVFB": "false"})
            # Set proper window size (Firefox) for screenshot
            # https://github.com/mozilla/geckodriver/issues/1354
            if self.browser_type == "firefox":
                params["environment"].update(
                    {"MOZ_HEADLESS_WIDTH": CONTAINER_WINDOW_WIDTH, "MOZ_HEADLESS_HEIGHT": CONTAINER_WINDOW_HEIGHT}
                )

        # Run container
        self.__container = self.docker_client.containers.run(**params)
        assert self.__container

        # Wait for Selenium server process to be ready
        self._wait_for_selenium_server_to_be_ready()

        if current_thread() is main_thread():
            # Register container cleanup as an exit handler
            atexit.register(self.delete)
            signal.signal(signal.SIGTERM, self.delete)

        return self

    def delete(self):
        """Delete browser container"""
        if self.__container:
            try:
                self.__container.remove(force=True)
            except docker.errors.NotFound:
                pass
            self.__container = None

    def open_browser(self, view_only: bool = False):
        """Open browser via noVNC"""
        options = f"?autoconnect=true&view_only={'true' if view_only else 'false'}"
        webbrowser.open_new(f"http://{self.selenium_server}:{self.novnc_port}{options}")

    @contextmanager
    def record_video(self, mp4_filename: str):
        """Record video during a test"""
        filename = convert_to_filename(mp4_filename)
        cmd = (
            f"ffmpeg -video_size {CONTAINER_WINDOW_WIDTH}x{CONTAINER_WINDOW_HEIGHT} "
            f"-framerate 15 -f x11grab -i :99.0 "
            f"-pix_fmt yuv420p {CONTAINER_VIDEO_DIR}/{filename}"
        )
        self._exec_run(cmd, detach=True)
        try:
            yield  # do test
        finally:
            # Stop recording
            cmd = "timeout 5 sh -c 'pkill -SIGINT ffmpeg && while [ $(pgrep ffmpeg) ]; do sleep 0.1; done'"
            self._exec_run(cmd)
            print(f"Video recorded: {Path(self.record_dir, filename)}")

    def _wait_for_selenium_server_to_be_ready(self, timeout: int = 30):
        start_time = time.time()
        url = f"http://{self.selenium_server}:{self.selenium_port}/status"
        while time.time() < start_time + timeout:
            try:
                r = requests.get(url, timeout=1)
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
                pass
            else:
                if r.ok and r.json()["value"].get("ready"):
                    break
                time.sleep(0.2)

        if time.time() > start_time + timeout:
            raise TimeoutError("Unable to connect Selenium server")

        if not self.headless:
            # Add extra wait for VNC server
            time.sleep(2)

    def _exec_run(self, cmd: str, detach: bool = False):
        """Run command with root user inside the container"""
        exit_code, output = self.__container.exec_run(
            cmd,
            user="root",
            tty=True,
            stdin=True,
            stdout=True,
            stderr=True,
            detach=detach,
        )

        if not detach and exit_code != 0:
            err = (
                f"Command ran in the container failed\n"
                f"- exit_code: {exit_code}\n"
                f"- output: {output.decode('utf-8')}"
            )
            print(err)

    def _adjust_port(self, port: int) -> int:
        """Adjust port number for each pytest-xdist worker. Add the digit part of worker_id (eg. gw1) to the port number"""
        if xdist_id := os.environ.get("PYTEST_XDIST_WORKER"):
            return port + int(xdist_id[2:])
        else:
            return port


def convert_to_filename(s: str):
    """Convert to a normalized filename with timestamp"""
    # Add timestamp
    name, ext = os.path.splitext(s)
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{name}_{timestr}{ext}"

    # Normalize
    filename = str(filename).strip().replace(" ", "_")
    filename = re.sub(r"(?u)[^-\w._]", "_", filename)
    filename = re.sub(r"_+", "_", filename)
    return filename
