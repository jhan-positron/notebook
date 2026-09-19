#!/usr/bin/env python3
"""Exercise a temporary launcher copy with fake Podman and migration commands."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import unittest


HERE = Path(__file__).resolve().parent
PODMAN = r'''#!/usr/bin/env python3
import json, os, subprocess, sys, time
from pathlib import Path
root = Path(os.environ["MOCK_ROOT"])
state_path = root / "state.json"
state = json.loads(state_path.read_text())
args = sys.argv[1:]
with (root / "events.jsonl").open("a") as out:
    out.write(json.dumps(["podman", *args]) + "\n")
if os.environ.get("ASSERT_NO_LOCK_FD"):
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)
        except FileNotFoundError:
            continue
        if target == str(root / "persist/.claude-box.lock"):
            sys.exit("Podman inherited the launcher lock on fd " + entry.name)

def spawn_monitor():
    if not os.environ.get("SPAWN_MONITOR"):
        return
    # Model conmon surviving its Podman parent while retaining inherited fds.
    # Redirect all streams so a leaked lock cannot also hang capture_output.
    code = """import sys, time
from pathlib import Path
root = Path(sys.argv[1])
(root / 'monitor-ready').touch()
deadline = time.monotonic() + 15
while not (root / 'monitor-release').exists() and time.monotonic() < deadline:
    time.sleep(0.01)
(root / 'monitor-done').touch()
"""
    monitor = subprocess.Popen(
        [sys.executable, "-c", code, str(root)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=False, start_new_session=True,
    )
    (root / "monitor-pid").write_text(str(monitor.pid))
    deadline = time.monotonic() + 5
    while not (root / "monitor-ready").exists():
        if monitor.poll() is not None or time.monotonic() >= deadline:
            sys.exit("Mock monitor did not become ready")
        time.sleep(0.01)

def save():
    state_path.write_text(json.dumps(state))
if args[:2] == ["container", "exists"]:
    if os.environ.get("FAIL_EXISTS"):
        sys.exit(125)
    sys.exit(0 if state["exists"] else 1)
if args[:2] == ["image", "exists"]:
    sys.exit(0)
if args[0] == "inspect":
    template = args[2]
    if "range .Mounts" in template:
        print(state["source"] + "\t" + state["destination"])
    elif template == "{{.Image}}":
        print("sha256:original-image")
    elif template == "{{.Id}}":
        print(state["id"])
    elif template == "{{.State.Status}}":
        print(state["status"])
    elif template == "{{.State.Status}} {{.State.Pid}}":
        if os.environ.get("STOP_FAILURE") == "inspectfailure" and state.get("stop_count"):
            print("Error: cannot inspect container", file=sys.stderr)
            sys.exit(125)
        print(state["status"], state["pid"])
    else:
        sys.exit("Unexpected inspect template: " + template)
elif args[0] == "stop":
    state["stop_count"] = state.get("stop_count", 0) + 1
    failure = os.environ.get("STOP_FAILURE")
    state.update(status="exited", pid=0)
    if failure and (state["stop_count"] == 1 or failure == "retryfails"):
        if failure in ("running", "stopping", "unknown", "created", "configured"):
            state.update(status=failure, pid=12345 if failure == "running" else 0)
        elif failure == "nonzeroPID":
            state["pid"] = 12345
        elif failure == "stopped":
            state["status"] = "stopped"
        save()
        if failure == "unrelatederror":
            print("Error: storage database unavailable", file=sys.stderr)
        else:
            print("Error: timed out waiting for file /var/tmp/test/storage/overlay-containers/" + state["id"] + "/userdata/exec-session/exit/" + state["id"], file=sys.stderr)
        sys.exit(125)
    save()
elif args[0] == "rm":
    if os.environ.get("FAIL_RM"):
        sys.exit(17)
    state["exists"] = False
    save()
elif args[0] == "run":
    if os.environ.get("FAIL_RUN"):
        sys.exit(18)
    if os.environ.get("BLOCK_RUN"):
        (root / "run-blocked").touch()
        deadline = time.monotonic() + 5
        while not (root / "run-release").exists():
            if time.monotonic() >= deadline:
                sys.exit("Mock run was never released")
            time.sleep(0.01)
    state.update(exists=True, status="running", pid=12345)
    save()
    spawn_monitor()
elif args[0] == "start":
    state.update(status="running", pid=12345)
    save()
    spawn_monitor()
elif args[0] == "exec":
    if "-it" in args:
        # The interactive shell must not retain the serialization lock.
        sys.exit(subprocess.run(["flock", "-n", str(root / "persist/.claude-box.lock"), "true"]).returncode)
    if os.environ.get("FAIL_VERIFY"):
        sys.exit(19)
else:
    sys.exit("Unexpected Podman command: " + repr(args))
'''

HELPER = r'''import json, os, sys
from pathlib import Path
root = Path(os.environ["MOCK_ROOT"])
apply = "--apply" in sys.argv
with (root / "events.jsonl").open("a") as out:
    out.write(json.dumps(["helper", "apply" if apply else "dry-run"]) + "\n")
if not apply and os.environ.get("FAIL_PREFLIGHT"):
    sys.exit(16)
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claude-box-launcher-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.persist = self.root / "persist"
        (self.persist / "codex-home").mkdir(parents=True)
        self.target = self.root / "home/codex-home-claude-test"
        self.target.parent.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        podman = self.bin / "podman"
        podman.write_text(PODMAN)
        podman.chmod(0o700)
        helper = self.root / "helper.py"
        helper.write_text(HELPER)
        original = (HERE / "claude-box.proposed").read_text()
        # All filesystem writes and external mutations are redirected to this fixture.
        modified = original.replace("PERSIST=/var/tmp/jhan/persist", "PERSIST=" + shlex.quote(str(self.persist)))
        modified = modified.replace("CONTAINER_CODEX_HOME=/home/jhan/codex-home-$CONTAINER_HOSTNAME", "CONTAINER_CODEX_HOME=" + shlex.quote(str(self.target)))
        modified = modified.replace("/home/jhan/claude-container/migrate-codex-home.py", shlex.quote(str(helper)))
        self.launcher = self.root / "claude-box"
        self.launcher.write_text(modified)
        self.env = {**os.environ, "HOSTNAME": "test", "MOCK_ROOT": str(self.root), "PATH": str(self.bin) + ":/usr/bin:/bin"}
        self.state = {"exists": True, "id": "a" * 64, "status": "running", "pid": 12345, "source": str(self.persist / "codex-home"), "destination": "/home/codex-home-claude-test"}
        self.save_state()
        self.addCleanup(self.release_monitor)

    def release_monitor(self):
        (self.root / "monitor-release").touch()
        if (self.root / "monitor-pid").exists():
            deadline = time.monotonic() + 5
            while not (self.root / "monitor-done").exists():
                if time.monotonic() >= deadline:
                    self.fail("Mock monitor did not exit after release")
                time.sleep(0.01)

    def save_state(self):
        (self.root / "state.json").write_text(json.dumps(self.state))

    def run_launcher(self, command, **environment):
        return subprocess.run(["bash", str(self.launcher), command], env={**self.env, **environment}, text=True, capture_output=True, timeout=10)

    def events(self):
        path = self.root / "events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def lock_probe(self):
        return subprocess.run(
            ["flock", "-n", str(self.persist / ".claude-box.lock"), "true"],
            text=True, capture_output=True, timeout=2,
        )

    def assert_surviving_monitor_does_not_hold_lock(self):
        self.assertTrue((self.root / "monitor-ready").exists())
        self.assertFalse((self.root / "monitor-done").exists())
        os.kill(int((self.root / "monitor-pid").read_text()), 0)
        self.assert_success(self.lock_probe())

    def assert_no_mutation(self):
        events = self.events()
        self.assertFalse(any(e[:2] in (["podman", "stop"], ["podman", "rm"], ["podman", "run"], ["helper", "apply"]) for e in events), events)

    def assert_stop_failure_preserves_data(self, failure, expected_stops=1):
        result = self.run_launcher("migrate-home", STOP_FAILURE=failure)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        events = self.events()
        self.assertEqual(sum(e[:2] == ["podman", "stop"] for e in events), expected_stops, events)
        self.assertFalse(any(e[:2] in (["podman", "rm"], ["helper", "apply"], ["podman", "run"]) for e in events), events)
        self.assertNotIn("recreated claude-dev", result.stdout)
        self.assertEqual((self.persist / ".codex-home-migration-image").read_text().strip(), "sha256:original-image")
        return result

    def mark_migration_pending(self):
        (self.persist / ".codex-home-migration-image").write_text("sha256:original-image\n")

    def assert_pending_warning(self, result):
        self.assert_success(result)
        self.assertIn("migrat", result.stderr.lower())
        self.assertIn("claude-box migrate-home", result.stderr)
        self.assertTrue((self.persist / ".codex-home-migration-image").exists())

    def test_existing_enter_does_not_migrate_and_unlocks(self):
        self.assert_success(self.run_launcher("enter", ASSERT_NO_LOCK_FD="1"))
        self.assert_no_mutation()
        self.assertFalse(any(e[0] == "helper" for e in self.events()))
        self.assertEqual(self.events()[-1][:3], ["podman", "exec", "-it"])

    def test_migration_podman_commands_do_not_inherit_lock_descriptor(self):
        self.assert_success(self.run_launcher("migrate-home", ASSERT_NO_LOCK_FD="1"))

    def test_migration_monitor_does_not_hold_lock_after_success(self):
        self.assert_success(self.run_launcher("migrate-home", SPAWN_MONITOR="1"))
        self.assert_surviving_monitor_does_not_hold_lock()
        self.assert_success(self.run_launcher("start"))

    def test_migration_monitor_does_not_hold_lock_after_verification_failure(self):
        result = self.run_launcher("migrate-home", SPAWN_MONITOR="1", FAIL_VERIFY="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.persist / ".codex-home-migration-image").exists())
        self.assert_surviving_monitor_does_not_hold_lock()

    def test_start_monitor_does_not_hold_lock_after_launcher_exits(self):
        self.state.update(status="exited", pid=0)
        self.save_state()
        self.assert_success(self.run_launcher("start", SPAWN_MONITOR="1"))
        self.assert_surviving_monitor_does_not_hold_lock()
        self.assert_success(self.run_launcher("enter"))

    def test_launcher_keeps_lock_while_podman_runs(self):
        self.state["exists"] = False
        self.save_state()
        process = subprocess.Popen(
            ["bash", str(self.launcher), "start"],
            env={**self.env, "BLOCK_RUN": "1", "ASSERT_NO_LOCK_FD": "1"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "run-blocked").exists():
                if process.poll() is not None or time.monotonic() >= deadline:
                    self.fail("Launcher did not reach the blocked Podman run")
                time.sleep(0.01)
            self.assertEqual(self.lock_probe().returncode, 1)
        finally:
            (self.root / "run-release").touch()
            stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assert_success(self.lock_probe())

    def test_migration_order_arguments_and_image(self):
        self.assert_success(self.run_launcher("migrate-home"))
        relevant = [e[:2] for e in self.events() if e[:2] in (["podman", "stop"], ["podman", "rm"], ["helper", "apply"], ["podman", "run"], ["podman", "exec"])]
        self.assertEqual(relevant, [["podman", "stop"], ["podman", "rm"], ["helper", "apply"], ["podman", "run"], ["podman", "exec"]])
        for event in self.events():
            if event[:2] in (["podman", "stop"], ["podman", "rm"]):
                self.assertEqual(event[-1], self.state["id"])
                self.assertNotIn("--force", event)
                self.assertNotIn("-f", event)
        run = next(e for e in self.events() if e[:2] == ["podman", "run"])
        self.assertIn("USER=jhan", run)
        self.assertIn("LOGNAME=jhan", run)
        for mount in ["/home/jhan:/home/jhan", "/scratch:/scratch", str(self.persist / "nix") + ":/nix", str(self.persist / "tron-main") + ":/var/tmp/tron-main", str(self.persist / "etc-nix") + ":/etc/nix", str(self.persist / "codex-home") + ":" + str(self.target)]:
            self.assertIn(mount, run)
        self.assertIn("sha256:original-image", run)
        self.assertFalse((self.persist / ".codex-home-migration-image").exists())

    def test_rm_failure_does_not_apply_or_run(self):
        self.assertNotEqual(self.run_launcher("migrate-home", FAIL_RM="1").returncode, 0)
        self.assertFalse(any(e[:2] in (["helper", "apply"], ["podman", "run"]) for e in self.events()))
        self.assertEqual((self.persist / ".codex-home-migration-image").read_text().strip(), "sha256:original-image")

    def test_preflight_failure_does_not_stop(self):
        self.assertNotEqual(self.run_launcher("migrate-home", FAIL_PREFLIGHT="1").returncode, 0)
        self.assert_no_mutation()

    def test_exists_error_does_not_migrate(self):
        result = self.run_launcher("migrate-home", FAIL_EXISTS="1")
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_mutation()

    def test_wrong_mount_destination_refused(self):
        self.state["destination"] = "/unexpected"
        self.save_state()
        self.assertNotEqual(self.run_launcher("migrate-home").returncode, 0)
        self.assert_no_mutation()

    def test_wrong_mount_source_refused(self):
        self.state["source"] = "/unexpected"
        self.save_state()
        self.assertNotEqual(self.run_launcher("migrate-home").returncode, 0)
        self.assert_no_mutation()

    def test_nonempty_destination_refused(self):
        self.target.mkdir()
        (self.target / "preserve.txt").write_text("must remain visible")
        self.assertNotEqual(self.run_launcher("migrate-home").returncode, 0)
        self.assert_no_mutation()

    def test_symlink_destination_refused(self):
        self.target.symlink_to(self.persist / "codex-home", target_is_directory=True)
        self.assertNotEqual(self.run_launcher("migrate-home").returncode, 0)
        self.assert_no_mutation()

    def test_failed_creation_retry_preserves_image(self):
        self.assertNotEqual(self.run_launcher("migrate-home", FAIL_RUN="1").returncode, 0)
        self.assert_success(self.run_launcher("migrate-home"))
        runs = [e for e in self.events() if e[:2] == ["podman", "run"]]
        self.assertEqual(len(runs), 2)
        self.assertTrue(all("sha256:original-image" in run for run in runs))

    def test_verification_failure_does_not_report_success(self):
        result = self.run_launcher("migrate-home", FAIL_VERIFY="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("recreated claude-dev", result.stdout)
        self.assertTrue((self.persist / ".codex-home-migration-image").exists())

    def test_exec_exit_timeout_retries_after_confirming_stopped(self):
        self.assert_success(self.run_launcher("migrate-home", STOP_FAILURE="exited"))
        events = self.events()
        stops = [i for i, event in enumerate(events) if event[:2] == ["podman", "stop"]]
        self.assertEqual(len(stops), 2, events)
        checks = [i for i, event in enumerate(events) if event[:2] == ["podman", "inspect"] and "{{.State.Status}} {{.State.Pid}}" in event]
        self.assertTrue(any(stops[0] < check < stops[1] for check in checks), events)
        removal = next(i for i, event in enumerate(events) if event[:2] == ["podman", "rm"])
        apply = next(i for i, event in enumerate(events) if event[:2] == ["helper", "apply"])
        self.assertLess(stops[1], removal)
        self.assertLess(removal, apply)
        for event in events:
            if event[:2] in (["podman", "stop"], ["podman", "rm"]):
                self.assertEqual(event[-1], self.state["id"])
                self.assertNotIn("--force", event)
                self.assertNotIn("-f", event)
        self.assertFalse((self.persist / ".codex-home-migration-image").exists())

    def test_exec_exit_timeout_accepts_stopped_state(self):
        self.assert_success(self.run_launcher("migrate-home", STOP_FAILURE="stopped"))
        self.assertEqual(sum(e[:2] == ["podman", "stop"] for e in self.events()), 2)

    def test_exec_exit_timeout_running_container_refused(self):
        self.assert_stop_failure_preserves_data("running")

    def test_exec_exit_timeout_stopping_container_refused(self):
        self.assert_stop_failure_preserves_data("stopping")

    def test_exec_exit_timeout_nonzero_process_id_refused(self):
        self.assert_stop_failure_preserves_data("nonzeroPID")

    def test_exec_exit_timeout_unknown_state_refused(self):
        self.assert_stop_failure_preserves_data("unknown")

    def test_exec_exit_timeout_created_state_refused(self):
        self.assert_stop_failure_preserves_data("created")

    def test_exec_exit_timeout_configured_state_refused(self):
        self.assert_stop_failure_preserves_data("configured")

    def test_exec_exit_timeout_failed_inspection_refused(self):
        self.assert_stop_failure_preserves_data("inspectfailure")

    def test_exec_exit_timeout_retry_failure_does_not_remove(self):
        self.assert_stop_failure_preserves_data("retryfails", expected_stops=2)

    def test_unrelated_stop_error_is_not_retried(self):
        result = self.assert_stop_failure_preserves_data("unrelatederror")
        self.assertIn("storage database unavailable", result.stderr)

    def test_already_stopped_container_migrates(self):
        self.state.update(status="exited", pid=0)
        self.save_state()
        self.assert_success(self.run_launcher("migrate-home"))
        events = self.events()
        removal = next(i for i, event in enumerate(events) if event[:2] == ["podman", "rm"])
        apply = next(i for i, event in enumerate(events) if event[:2] == ["helper", "apply"])
        self.assertLess(removal, apply)
        self.assertEqual(events[removal][-1], self.state["id"])

    def test_pending_migration_enter_warns_and_preserves_access(self):
        self.mark_migration_pending()
        self.assert_pending_warning(self.run_launcher("enter"))
        self.assert_no_mutation()
        self.assertEqual(self.events()[-1][:3], ["podman", "exec", "-it"])

    def test_pending_migration_running_start_warns(self):
        self.mark_migration_pending()
        self.assert_pending_warning(self.run_launcher("start"))
        self.assert_no_mutation()

    def test_pending_migration_stopped_start_warns_and_preserves_access(self):
        self.state.update(status="exited", pid=0)
        self.save_state()
        self.mark_migration_pending()
        self.assert_pending_warning(self.run_launcher("start"))
        self.assert_no_mutation()
        self.assertIn(["podman", "start", "claude-dev"], self.events())


if __name__ == "__main__":
    unittest.main(verbosity=2)
