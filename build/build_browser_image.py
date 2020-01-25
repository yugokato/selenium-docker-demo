#!/usr/bin/env python3

####################################################################################################
# Python script for building custom Chrome/Firefox images with a version of your choice.
# The following SeleniumHQ official images will be used as base images.
#  - selenium/standalone-chrome-debug
#  - selenium/standalone-firefox-debug
#
# Final images will be named as selenium-chrome:<tag> and selenium-firefox:<tag>
# where each tag is the browser version (and "latest" for the latest version)
#
#
# Usage:
#   ~/selenium-docker-demo$ ./build/build_browser_image.py [OPTIONS]
#
# Available Options:
#   ~/selenium-docker-demo$ ./build/build_browser_image.py -h
#   usage: build_browser_image.py [-h] [-b [BROWSER [BROWSER ...]]]
#                                 [--chrome-version CHROME_VERSION]
#                                 [--firefox-version FIREFOX_VERSION] [-f]
#
#   optional arguments:
#     -h, --help            show this help message and exit
#     -b [BROWSER [BROWSER ...]], --browser [BROWSER [BROWSER ...]]
#                           Target browser to build image. Defaults to build both
#                           Chrome and Firefox
#     --chrome-version CHROME_VERSION
#                           Chrome version
#     --firefox-version FIREFOX_VERSION
#                           Firefox version
#     -f, --force           Force build image even when an image for the desired
#                           version exists
####################################################################################################

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from functools import wraps
from io import BytesIO
from pathlib import Path

import docker
import requests
from bs4 import BeautifulSoup, SoupStrainer
from docker import errors


SUPPORTED_BROWSERS = ["chrome", "firefox"]
CHROME_BUILD_CMD = (
    "VERSION={browser_version} "
    'BUILD_ARGS="'
    "--build-arg CHROME_VERSION=google-chrome-stable={browser_version}-1 "
    '--build-arg CHROME_DRIVER_VERSION={driver_version}" '
    "make standalone_chrome_debug"
)
FIREFOX_BUILD_CMD = (
    "VERSION={browser_version} "
    'BUILD_ARGS="'
    "--build-arg FIREFOX_VERSION={browser_version} "
    '--build-arg GECKODRIVER_VERSION={driver_version}" '
    "make standalone_firefox_debug"
)
Dockerfile = (
    # Add capability to record video
    "FROM {base_image}\n"
    "RUN sudo apt-get update"
    " && sudo apt-get install -y ffmpeg"
    " && sudo rm -rf /var/lib/apt/lists/*\n"
    "RUN mkdir /home/seluser/videos"
)


def build_image(browser_name, desired_browser_version="latest", force=False):
    """Build custom browser image on top of selenium/standalone-{browser_name}-debug image.

    Arguments:
        browser_name (str): Browser type (chrome/firefox)
        desired_browser_version (str): Browser version that you would like to build
        force (bool): Force build even when the image already exists

    Note:
        Unfortunately Chrome does not keep old versions. As a workaround, if an old
        version is specified to desired_browser_version, the script will access the
        SeleniumHQ release page (https://github.com/SeleniumHQ/docker-selenium/releases)
        and will attempt to find a release the requested Chrome version was installed on.
        From there, our custom image will be built from the located
        selenium/standalone-chrome-debug:<release_tag>

    Final images:
        - selenium-{browser_name}:{desired_browser_version}
        - selenium-{browser_name}:latest (if version=latest)
    """

    def skip_if_exists(f):
        """Decorator to check if an image for the desired version already exists"""

        @wraps(f)
        def wrapped_func(*args, **kwargs):
            self = args[0]  # type: BrowserImageBuilder
            if self.desired_browser_version == "latest":
                # Wait until buildable browser version is located
                tag_to_check = self.buildable_browser_version
            else:
                tag_to_check = self.desired_browser_version
            if tag_to_check:
                image = f"{self.local_repository}:{tag_to_check}"
                try:
                    self.docker_client.images.get(image)
                    if not self.force:
                        print(f"SKIPPED: {image} already exists.")
                        return
                except errors.ImageNotFound:
                    pass
            return f(*args, **kwargs)

        return wrapped_func

    class BrowserImageBuilder(object):
        """Base class for browser image builder"""

        docker_client = docker.from_env()

        def __init__(self, browser_name, desired_browser_version="latest", force=False):
            self.browser_name = browser_name
            self.desired_browser_version = desired_browser_version
            self.buildable_browser_version = None
            self.driver_name = None
            self.driver_version = None
            self.force = force
            self.local_repository = f"selenium-{browser_name}"
            self.base_image_name = None
            self.final_image_name = None

        @skip_if_exists
        def build(self, base_image=None):
            """Build selenium-docker image

            Arguments:
                base_image (str, optional): Base image name to build from
            """
            assert self.buildable_browser_version and self.driver_version
            self.final_image_name = (
                f"{self.local_repository}:{self.buildable_browser_version}"
            )
            print("######################################################")
            print(f"# {self.browser_name} version: {self.buildable_browser_version}")
            print(f"# {self.driver_name} version: {self.driver_version}")
            print("######################################################")

            if base_image:
                self._build_custom_image(base_image)
            else:
                with self._download_docker_selenium_repo() as build_dir:
                    with self._build_base_image(build_dir) as base_image:
                        self._build_custom_image(base_image)

            # If latest version, put "latest" tag on the image
            if self.desired_browser_version == "latest":
                custom_img = self.docker_client.images.get(self.final_image_name)
                custom_img.tag(self.local_repository, tag="latest")

        def get_latest_version(self):
            raise NotImplementedError

        def get_driver_version(self):
            raise NotImplementedError

        @contextmanager
        def _download_docker_selenium_repo(self):
            """Download SeleniumHQ docker-selenium official repository from github, and delete it at the end"""

            class ZipFile(zipfile.ZipFile):
                """Custom ZipFile class that solves the permission issue https://bugs.python.org/issue15795"""

                def _extract_member(self, member, targetpath, pwd):
                    if not isinstance(member, zipfile.ZipInfo):
                        member = self.getinfo(member)
                    targetpath = super()._extract_member(member, targetpath, pwd)
                    attr = member.external_attr >> 16
                    if attr != 0:
                        os.chmod(targetpath, attr)
                    return targetpath

            tmp_dir = tempfile.mkdtemp()
            try:
                # download
                url = "https://github.com/SeleniumHQ/docker-selenium/archive/master.zip"
                r = requests.get(url)
                if r.status_code != 200:
                    Exception("Failed to download docker-selenium local_repository")
                zip_file_path = Path(tmp_dir, "repo.zip")
                with open(zip_file_path, "wb") as f:
                    f.write(r.content)

                # unzip
                with ZipFile(zip_file_path) as zip:
                    zip.extractall(tmp_dir)

                docker_selenium_dir = Path(tmp_dir, "docker-selenium-master")
                yield docker_selenium_dir  # build images
            finally:
                # Cleanup
                shutil.rmtree(tmp_dir)

        @contextmanager
        def _build_base_image(self, build_dir):
            """Build docker-selenium images with the desired browser version

            Reference: https://github.com/SeleniumHQ/docker-selenium/wiki/Building-your-own-images

            This context manager will build the following images, which will be deleted at the end
                - selenium/base
                - selenium/node-base
                - selenium/node-{browser_name}
                - selenium/node-{browser_name}-debug
                - selenium/standalone-{browser_name}-debug  (The base image we need)
            """
            print(f"\n#################### Building base image ####################")
            try:
                if self.browser_name == "chrome":
                    build_cmd = CHROME_BUILD_CMD.format(
                        browser_version=self.buildable_browser_version,
                        driver_version=self.driver_version,
                    )
                else:
                    build_cmd = FIREFOX_BUILD_CMD.format(
                        browser_version=self.buildable_browser_version,
                        driver_version=self.driver_version,
                    )

                process = subprocess.Popen(
                    build_cmd, cwd=build_dir, shell=True, stdout=subprocess.PIPE
                )
                build_output = ""
                for line in iter(process.stdout.readline, b""):
                    line = line.decode("utf-8")
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    build_output += line

                base_image_name = (
                    f"selenium/standalone-{self.browser_name}-debug:"
                    f"{self.buildable_browser_version}"
                )
                if f"Successfully tagged {base_image_name}" not in build_output:
                    raise Exception("Build failed")

                yield base_image_name
            finally:
                # Delete all selenium/* images built for this version
                images = self.docker_client.images.list(
                    name=f"selenium/*:{self.buildable_browser_version}"
                )
                for image in images:
                    if image.tags:
                        image_name = image.tags[0]
                        try:
                            self.docker_client.images.remove(
                                image=image_name, force=True
                            )
                        except docker.errors.APIError:
                            pass

        def _build_custom_image(self, base_image_name):
            """Build custom image from the base image"""
            print(
                "\n"
                "#################### Building custom image ####################\n"
                f"# Base image: {base_image_name}\n"
                f"# Final image: {self.final_image_name}\n"
                "###############################################################"
            )
            dockerfile = Dockerfile.format(base_image=base_image_name)
            with BytesIO(dockerfile.encode("utf-8")) as f:
                build_params = dict(
                    tag=self.final_image_name,
                    fileobj=f,
                    cache_from=[base_image_name],
                    decode=True,
                    rm=True,
                    forcerm=True,
                )
                build_output = self.docker_client.api.build(**build_params)

                # Stream build output
                for chunk in build_output:
                    if "stream" in chunk:
                        sys.stdout.write(chunk["stream"])
                        sys.stdout.flush()
                print("\n")

            # Delete base image
            self.docker_client.images.remove(image=base_image_name, force=True)

    class ChromeImageBuilder(BrowserImageBuilder):
        """Chrome browser image builder"""

        def __init__(self, desired_browser_version, force=False):
            super().__init__(
                browser_name="chrome",
                desired_browser_version=desired_browser_version,
                force=force,
            )
            self.driver_name = "chromedriver"

        @skip_if_exists
        def build(self):
            base_image = None
            if self.desired_browser_version == "latest":
                print(f"Checking Chrome latest version...")
                self.buildable_browser_version = self.get_latest_version()
                self.driver_version = self.get_driver_version()
            else:
                base_image = self.get_old_chrome_base_image()
                tag = base_image.split(":")[-1]
                self.buildable_browser_version = self.desired_browser_version
                self.driver_version = f"Unknown (Check SeleniumHQ '{tag}' release info)"

            super().build(base_image=base_image)

        def get_latest_version(self):
            """Get latest Chrome stable version"""
            latest_version = ""
            url = "http://omahaproxy.appspot.com/all.json"
            r = requests.get(url)
            if r.status_code == 200:
                for platform in r.json():
                    if platform["os"] == "linux":
                        versions = platform["versions"]
                        for version in versions:
                            if version["channel"] == "stable":
                                latest_version = version["current_version"]

            if not latest_version:
                err = f"Unable to locate the Chrome latest version"
                raise Exception(err)

            return latest_version

        def get_driver_version(self):
            """Get compatible chromedriver version for the browser version"""
            assert self.buildable_browser_version
            compatible_driver_version = None
            major_version = self.buildable_browser_version.rsplit(".", 1)[0]
            url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            r = requests.get(url)
            if r.ok:
                compatible_driver_version = r.text
            if not compatible_driver_version:
                err = (
                    f"Unable to locate a compatible chromedriver version for Chrome "
                    f"{self.buildable_browser_version}"
                )
                raise Exception(err)
            return compatible_driver_version

        def get_old_chrome_base_image(self):
            """Locate an official SeleniumHQ image the desired Chrome version was installed on"""
            print(
                f"Checking if there is any SeleniumHQ release for Chrome {self.desired_browser_version}..."
            )
            url = "https://github.com/SeleniumHQ/docker-selenium/releases"
            release_tag = None
            while True:
                r = requests.get(url)
                if not r.ok:
                    raise Exception(r.text)

                parse_only = SoupStrainer(class_="release-entry")
                bs = BeautifulSoup(r.text, "html.parser", parse_only=parse_only)
                for release in bs.contents:
                    li_list = release.find_all("li")
                    for li in li_list:
                        if (
                            f"Google Chrome: {self.desired_browser_version}"
                            in li.get_text()
                        ):
                            release_tag = release.select_one(
                                ".release-header a"
                            ).get_text(strip=True)
                            if release_tag.startswith("Selenium "):
                                # Some old releases have different release header. Convert to a relase tag
                                release_tag = (
                                    release_tag.replace("Selenium ", "")
                                    .replace(" ", "-")
                                    .lower()
                                )
                            assert release_tag
                            break

                # Check next page
                parse_only = SoupStrainer(class_="pagination")
                bs = BeautifulSoup(r.text, "html.parser", parse_only=parse_only)
                a = bs.select("a")
                if a and a[-1].get_text() == "Next":
                    url = a[-1].get("href")
                else:
                    # No more page
                    break

            if not release_tag:
                err = (
                    f"Unable to locate a base image released from SeleniumHQ that is compatible with "
                    f"Chrome version {self.desired_browser_version}"
                )
                raise Exception(err)

            return f"selenium/standalone-chrome-debug:{release_tag}"

    class FirefoxImageBuilder(BrowserImageBuilder):
        """Firefox browser image builder"""

        def __init__(self, desired_browser_version, force=False):
            super().__init__(
                browser_name="firefox",
                desired_browser_version=desired_browser_version,
                force=force,
            )
            self.driver_name = "geckodriver"

        @skip_if_exists
        def build(self):
            if self.desired_browser_version == "latest":
                print(f"Checking Firefox latest version...")
                self.buildable_browser_version = self.get_latest_version()
                self.driver_version = self.get_driver_version()
            else:
                if not self.is_valid_firefox_version():
                    err = f"'{self.desired_browser_version}' is not a valid Firefox version"
                    raise Exception(err)
                self.buildable_browser_version = self.desired_browser_version
                self.driver_version = self.get_driver_version()

            super().build()

        def get_latest_version(self):
            """Get latest Firefox version"""
            latest_version = ""
            url = "https://product-details.mozilla.org/1.0/firefox_versions.json"
            r = requests.get(url)
            if r.ok:
                latest_version = r.json().get("LATEST_FIREFOX_VERSION")

            if not latest_version:
                err = f"Unable to locate the Firefox latest version"
                raise Exception(err)

            return latest_version

        def get_driver_version(self):
            """Get compatible geckodriver version for the browser version"""
            assert self.buildable_browser_version
            compatible_driver_version = None
            major_version = self.buildable_browser_version.split(".", 1)[0]
            url = "https://firefox-source-docs.mozilla.org/testing/geckodriver/Support.html"
            r = requests.get(url)
            if r.ok:
                # Use html5lib since the default parser doesn't handle elements with no ending tags correctly
                bs = BeautifulSoup(r.text, "html5lib")
                for row in bs.tbody.find_all("tr"):
                    columns = row.find_all("td")
                    assert (
                        len(columns) == 4
                    )  # Will need to update the logic if table schema changes
                    compatible_driver_version = columns[0].get_text(strip=True)
                    min_firefox_version = columns[2].get_text(strip=True)
                    if int(major_version) >= int(min_firefox_version):
                        break
            if not compatible_driver_version:
                err = (
                    f"Unable to locate a compatible geckodriver version for Firefox "
                    f"{self.buildable_browser_version}"
                )
                raise Exception(err)
            return compatible_driver_version

        def is_valid_firefox_version(self):
            """Check the given Firefox version is an official one"""
            url = "https://www.mozilla.org/en-US/firefox/releases/"
            r = requests.get(url)
            if not r.ok:
                raise Exception(r.text)
            parse_only = SoupStrainer("ol", class_="c-release-list")
            bs = BeautifulSoup(r.text, "html.parser", parse_only=parse_only)
            firefox_version_links = bs.find_all("a")
            firefox_versions = [a.get_text(strip=True) for a in firefox_version_links]
            return self.desired_browser_version in firefox_versions

    ##### Build image #####
    if browser_name == "chrome":
        builder = ChromeImageBuilder
    else:
        builder = FirefoxImageBuilder
    try:
        builder(desired_browser_version, force=force).build()
    except KeyboardInterrupt:
        print("aborted")
        sys.exit()
    finally:
        builder.docker_client.images.prune()


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
        help="Target browser to build image. Defaults to build both Chrome and Firefox",
    )
    parser.add_argument(
        "--chrome-version",
        dest="chrome_version",
        default="latest",
        help="Chrome version",
    )
    parser.add_argument(
        "--firefox-version",
        dest="firefox_version",
        default="latest",
        help="Firefox version",
    )
    parser.add_argument(
        "-f",
        "--force",
        dest="force",
        action="store_true",
        default=False,
        help="Force build image even when an image for the desired version exists",
    )
    args = vars(parser.parse_args())
    return args


if __name__ == "__main__":
    args = parse_arguments()
    browsers = args["browsers"]
    force = args["force"]

    for browser_name in browsers:
        desired_version = args[f"{browser_name}_version"]
        build_image(browser_name, desired_browser_version=desired_version, force=force)
