#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
########################################################################################################################
# Python script for building custom Chrome/Firefox/Edge images based on selenium/standalone-{chrome|firefox|edge} image
# Final images will be named as selenium-{chrome|firefox|edge}:latest
#
#
# selenium-docker-demo$ ./scripts/build_browser_image.py -h
# usage: build_browser_image.py [-h] [-b [BROWSER [BROWSER ...]]]
#
# optional arguments:
#   -h, --help            show this help message and exit
#   -b [BROWSER [BROWSER ...]], --browser [BROWSER [BROWSER ...]]
#                         Target browser(s) to build image. Defaults to build all 3 browsers (chrome, firefox, edge)
########################################################################################################################

import argparse
import curses
from curses import window
from io import BytesIO
from itertools import chain
from typing import Any, Dict, Iterator, Optional, Tuple

import docker
from docker.errors import DockerException

from libraries.browser_container import SUPPORTED_BROWSERS

SELENIUM_BASE_IMAGE_TAG = "4.1"
DOCKERFILE = (
    # Add capability to record video
    "FROM {base_image}\n"
    "RUN sudo apt-get update"
    " && sudo apt-get install -y ffmpeg"
    " && sudo rm -rf /var/lib/apt/lists/*\n"
    "RUN mkdir -p /tmp/screencast"
)


class BrowserImageBuilder(object):
    """Custom browser image builder

    This class build custom browser images on top of the following official Selenium standalone images
    - selenium/standalone-chrome:<SELENIUM_BASE_IMAGE_TAG>
    - selenium/standalone-firefox:<SELENIUM_BASE_IMAGE_TAG>
    - selenium/standalone-edge:<SELENIUM_BASE_IMAGE_TAG>
    """

    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except DockerException:
        sys.exit("ERROR: Unable to connect to the Docker daemon. Is the docker daemon running on this host?")

    def __init__(self, browser_name: str):
        self.browser_name = browser_name.lower()
        self.base_image_name = f"selenium/standalone-{browser_name}:{SELENIUM_BASE_IMAGE_TAG}"
        self.final_image_name = f"selenium-{browser_name}:latest"

    def build(self):
        """Build custom image from the base image"""
        print(
            "#################### Building custom image ####################\n"
            f"# Base image: {self.base_image_name}\n"
            f"# Final image: {self.final_image_name}\n"
            "###############################################################"
        )
        dockerfile = DOCKERFILE.format(base_image=self.base_image_name)
        with BytesIO(dockerfile.encode("utf-8")) as f:
            build_params = dict(tag=self.final_image_name, fileobj=f, decode=True, rm=True, forcerm=True)
            build_generator = self.docker_client.api.build(**build_params)
            build_output = self._stream_output(build_generator)
            if not build_output.endswith(f"Successfully tagged {self.final_image_name}\n"):
                raise Exception("Build failed")

        # Delete base image
        self.docker_client.images.remove(image=self.base_image_name, force=True)

    def _stream_output(self, build_generator: Iterator[Dict[str, Any]]) -> str:
        """Stream build output on the console"""

        def write(output: str):
            sys.stdout.write(output)
            sys.stdout.flush()

        def stream_image_pull_output(
            screen: window, generator: Iterator[Dict[str, Any]]
        ) -> Tuple[str, Optional[Exception]]:
            layer_ids = []
            pull_output = ""
            exception = None
            num_rows, num_cols = screen.getmaxyx()
            try:
                for chunk in generator:
                    if all(key in chunk for key in ["status", "id"]):
                        num_rows, num_cols = screen.getmaxyx()
                        layer_id = chunk["id"]
                        if layer_id not in layer_ids:
                            layer_ids.append(layer_id)
                        if (y := layer_ids.index(layer_id)) <= num_rows:
                            status = chunk["status"]
                            progress = chunk.get("progress", " " * (num_cols - len(layer_id) - len(status) - 3))
                            screen.addstr(y, 0, f"{layer_id}: {status} {progress or ''}")
                            screen.refresh()
                    else:
                        break
            except BaseException as e:
                exception = e
            finally:
                for row in range(num_rows):
                    if (line := screen.instr(row, 0).decode("utf-8")).strip():
                        pull_output += line
                return pull_output, exception

        build_output = ""
        for chunk in build_generator:
            output = None
            if "stream" in chunk:
                output = chunk["stream"]
                write(output)
            elif "status" in chunk:
                if "id" in chunk:
                    output, exception = curses.wrapper(stream_image_pull_output, chain([chunk], build_generator))
                    write(output)
                    if exception:
                        raise exception
                else:
                    output = chunk["status"]
                    write(output + "\n")
            if output:
                build_output += output
        write("\n")
        return build_output


def parse_arguments():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        "--browser",
        nargs="*",
        metavar="BROWSER",
        dest="browsers",
        choices=SUPPORTED_BROWSERS,
        default=SUPPORTED_BROWSERS,
        help=f"Target browser(s) to build image. Defaults to build all browsers ({', '.join(SUPPORTED_BROWSERS)})",
    )
    args = vars(parser.parse_args())
    return args


if __name__ == "__main__":
    try:
        args = parse_arguments()
        for browser in args["browsers"]:
            BrowserImageBuilder(browser).build()
    except KeyboardInterrupt:
        print("Cancelled")
