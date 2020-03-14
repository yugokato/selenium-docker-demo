import os
import re
import time
from pathlib import Path
from contextlib import contextmanager

import docker
import docker.errors
import requests

from .vnc_client import DEFAULT_VNC_PORT

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from docker.models.containers import Container


DEFAULT_SELENIUM_PORT = 4444
SELENIUM_SERVER_IP = "127.0.0.1"
CONTAINER_VIDEO_DIR = "/home/seluser/videos"
CONTAINER_WINDOW_WIDTH = "1360"
CONTAINER_WINDOW_HEIGHT = "1020"


class BrowserContainer(object):
    """Browser container class"""

    def __init__(
        self, browser_type, browser_version, index=0, headless=False, record_dir=None
    ):
        self.docker_client = docker.from_env()
        self.browser_type = browser_type
        self.browser_version = browser_version
        self.headless = headless
        self.record_dir = record_dir
        self.selenium_port = DEFAULT_SELENIUM_PORT + index
        self.vnc_port = DEFAULT_VNC_PORT + index
        self.__container = None  # type: Optional[Container]

        if record_dir is None:
            self.record_dir = str(Path(__file__).parents[1] / "videos")
        Path(self.record_dir).mkdir(exist_ok=True)

    def run(self):
        """Run browser container"""
        # Generate container parameters
        image_name = f"selenium-{self.browser_type}:{self.browser_version}"
        params = dict(
            image=image_name,
            ports={
                f"{DEFAULT_SELENIUM_PORT}/tcp": self.selenium_port,
                f"{DEFAULT_VNC_PORT}/tcp": self.vnc_port,
            },
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
                    {
                        "MOZ_HEADLESS_WIDTH": CONTAINER_WINDOW_WIDTH,
                        "MOZ_HEADLESS_HEIGHT": CONTAINER_WINDOW_HEIGHT,
                    }
                )

        # Run container
        self.__container = self.docker_client.containers.run(**params)
        assert self.__container

        # Wait for Selenium server process to be ready
        self._wait_for_selenium_server_to_be_ready()

        if not self.headless:
            # Add extra wait for VNC server
            time.sleep(2)

        return self

    def delete(self):
        """Delete browser container"""
        try:
            self.__container.remove(force=True)
        except docker.errors.NotFound:
            pass
        self.__container = None

    @contextmanager
    def record_video(self, mp4_filename):
        """Record video during a test

        Arguments:
            mp4_filename (str): File name (.mp4)
        """
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

    def _wait_for_selenium_server_to_be_ready(self, timeout=30):
        start_time = time.time()
        url = f"http://{SELENIUM_SERVER_IP}:{self.selenium_port}/wd/hub/status"
        while time.time() < start_time + timeout:
            try:
                r = requests.get(url, timeout=1)
            except requests.exceptions.ConnectionError:
                pass
            else:
                if r.ok and r.json()["value"].get("ready"):
                    break
                time.sleep(0.2)

        if time.time() > start_time + timeout:
            raise TimeoutError("Unable to connect Selenium server")

    def _exec_run(self, cmd, detach=False):
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


def convert_to_filename(s):
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
