import shlex
import subprocess
import sys
from contextlib import contextmanager

DEFAULT_VNC_PORT = 5900


class VncClient(object):
    """RealVNC Client

    Note:
        Requires RealVNC Viewer to be installed
        https://www.realvnc.com/en/connect/download/viewer/
    """

    def __init__(self, host="127.0.0.1", port=DEFAULT_VNC_PORT):
        self.platform = sys.platform
        if self.platform not in ["linux", "linux2", "darwin"]:
            raise Exception("Unsupported platform")

        self.host = host
        self.port = port

    @contextmanager
    def connect(self):
        """Context manager too connect to a VNC server, disconnect at the end"""
        realvnc_server = f"{self.host}:{self.port}"
        realvnc_options = "WarnUnencrypted=0 ViewOnly=1"

        if self.platform == "darwin":
            cmd = (
                f'open -a "/Applications/VNC Viewer.app" -n '
                f"--args {realvnc_server} {realvnc_options}"
            )
            shell = True
        else:
            cmd = shlex.split(f"vncviewer {realvnc_server} {realvnc_options}")
            shell = False

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            shell=shell,
        )
        try:
            yield
        finally:
            proc.kill()
