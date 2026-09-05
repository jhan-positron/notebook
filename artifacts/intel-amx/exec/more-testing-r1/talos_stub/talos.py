"""No-op stand-in for the `talos` reporting library used by systems_test.

systems_test's perf and soak code call talos.session.{log,graph,sample,
describe,artifact} and wrap entry points in @talos.testcase. The real
package writes every call to the CI results database (MongoDB) and Slack.
This stub keeps the calls local so an ad-hoc run leaves no trace in CI
records. Put this directory FIRST on PYTHONPATH so it shadows the installed
package.
"""
import logging
import time
import uuid


class _Session:
    def __init__(self):
        self.log = logging.getLogger("talos")
        self.uuid = "local-" + uuid.uuid4().hex[:12]
        self.start_time = time.time()
        self.local = True
        self.running = True
        self.db = None

    def describe(self, **kwds):
        return None

    def graph(self, *args, **kwds):
        return None

    def sample(self, *args, **kwds):
        return None

    def artifact(self, *args, **kwds):
        return None

    def message(self, *args, **kwds):
        return None


session = _Session()


def testcase(func):
    def run(*args, **kwds):
        return func(session, *args, **kwds)
    run.__name__ = getattr(func, "__name__", "testcase")
    return run
