import re

from py.log import Producer  # noqa
from xdist.scheduler import LoadScopeScheduling

from libraries.browser_container import SUPPORTED_BROWSERS


class LoadBrowserScheduling(LoadScopeScheduling):
    """Custom pytest-xdist load scheduling logic

    Implement load scheduling across nodes, but grouping test by browser
    """

    def __init__(self, config, log=None):
        super().__init__(config, log)
        self.num_browsers = len(config.option.browsers)
        if log is None:
            self.log = Producer("loadfilesched")
        else:
            self.log = log.loadfilesched

    def _split_scope(self, nodeid):
        """Determine the scope (grouping) of a nodeid

        Each test nodeid should contain "(<browser>:<version>)".
            - example/test.py::test[(chrome:latest)]
            - example/test.py::test[(firefox:latest)]
            - example/test.py::test[(edge:latest)]
        """
        if self.num_browsers > 1:
            pattern = re.compile(rf".+\((?P<browser>{'|'.join(SUPPORTED_BROWSERS)}):(?P<version>.+)\).+")
            matched = re.search(pattern, nodeid)
            if matched:
                return f"{matched.group('browser')}:{matched.group('version')}"
        return super()._split_scope(nodeid)
