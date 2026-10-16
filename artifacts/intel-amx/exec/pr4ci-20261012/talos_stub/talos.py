"""Recording stand-in for the `talos` reporting library used by systems_test.

systems_test's perf code calls talos.session.{log,graph,sample,describe,
artifact,message} and wraps entry points in @talos.testcase. The real
package writes every call to the CI results database (MongoDB) and Slack.
This stub keeps the calls local (nothing reaches CI records) and RECORDS the
sample() and describe() calls to the JSON file named by $TALOS_STUB_OUT, so
the model-load durations and per-model perf durations the harness reports to
Talos are kept with our results. Put this directory FIRST on PYTHONPATH so it
shadows the installed package.
"""
import json
import logging
import os
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
        self.samples = []
        self.descriptions = []
        self.out = os.environ.get("TALOS_STUB_OUT")

    def _flush(self):
        if not self.out:
            return
        try:
            with open(self.out, "w") as f:
                json.dump({"samples": self.samples, "descriptions": self.descriptions}, f, indent=1, default=str)
        except Exception as exc:  # never let bookkeeping break the benchmark
            self.log.warning("talos stub could not write %s: %s", self.out, exc)

    def describe(self, **kwds):
        self.descriptions.append({"t": time.time(), **kwds})
        self._flush()

    def graph(self, *args, **kwds):
        return None

    def sample(self, *args, **kwds):
        self.samples.append({"t": time.time(), **kwds})
        self._flush()

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
