#!/usr/bin/env python3
"""Model checker by exhaustive search for TRON's capture slot protocol.

The model mirrors tron::trace_detail::capture_controller
(src/pos/trace_capture.cpp, tron commit 7eddde7895, 2026-11-21).
CaptureSlot.tla in this folder is the same model in TLA+ syntax.

What the script does is what TLC (the TLA+ model checker) does:
  1. Start from the initial state.
  2. Apply every step that any thread could take next.
  3. Visit every reachable state once (breadth first).
  4. Test each rule in each state.
  5. On a failure, print the shortest list of steps that leads to it.

Run: python3 -I capture_slot_check.py
"""
from collections import deque, namedtuple

# One state of the model. Each field stands for one C++ variable.
State = namedtuple("State", [
    "slot",      # "empty", or active_->state: accepted/waiting/recording/stopping
    "slot_id",   # active_->id as a number, 0 when the slot is empty
    "stop_req",  # active_->stop_requested
    "sigusr1",   # sigusr1_active_
    "worker",    # where the worker thread is: idle/setup/aborting/recording/stopping
    "job",       # id of the record that take_start() gave the worker, 0 when idle
    "next_id",   # next_sequence_
])

INIT = State("empty", 0, False, False, "idle", 0, 1)
MAX_STARTS = 3  # the model tries at most 3 start commands


def free(s):
    """finish_locked(): the record leaves the slot."""
    return s._replace(slot="empty", slot_id=0, stop_req=False)


def steps(s, variant):
    """Every (step name, next state) that some thread can take from state s.

    Each controller method holds the mutex for its whole body, so one method
    call is one step. variant selects the real design or one seeded bug.
    """
    out = []

    # ---- FUSE request thread: command() -------------------------------
    start_allowed = s.slot == "empty" and (
        not s.sigusr1 or variant == "start_ignores_sigusr1")
    if s.next_id <= MAX_STARTS and start_allowed:
        out.append((f"FUSE: start -> capture {s.next_id} accepted",
                    s._replace(slot="accepted", slot_id=s.next_id,
                               stop_req=False, next_id=s.next_id + 1)))
    if s.slot == "accepted":  # "The worker never saw it: no window."
        out.append((f"FUSE: stop capture {s.slot_id} -> stopped_before_start,"
                    " slot empty", free(s)))
    elif s.slot != "empty" and not s.stop_req:
        out.append((f"FUSE: stop capture {s.slot_id} -> stop_requested = true",
                    s._replace(stop_req=True)))

    # ---- capture worker thread ----------------------------------------
    if s.worker == "idle" and s.slot == "accepted":
        # take_start(): accepted -> waiting. The seeded bug leaves it accepted.
        new_slot = "accepted" if variant == "no_waiting_state" else "waiting"
        out.append((f"worker: take_start() returns capture {s.slot_id}",
                    s._replace(slot=new_slot, worker="setup", job=s.slot_id)))
    # begin_recording(), set_stopping() and finish_locked() start with
    # TRON_ASSERT(active_). With an empty slot the process aborts there, so the
    # model gives the worker no further step. The AssertActive rule reports it.
    if s.worker != "idle" and s.slot != "empty":
        if s.worker == "setup":
            # File or Perfetto session setup failed: finish(failed).
            out.append((f"worker: setup of capture {s.job} fails"
                        " -> finish(failed), slot empty",
                        free(s)._replace(worker="idle", job=0)))
            if s.stop_req:  # begin_recording() returns false
                out.append(("worker: begin_recording() sees the stop request",
                            s._replace(worker="aborting")))
            else:
                out.append((f"worker: begin_recording() marks capture"
                            f" {s.slot_id} as recording"
                            f" (the worker runs capture {s.job})",
                            s._replace(slot="recording", worker="recording")))
        elif s.worker == "aborting":
            if variant == "abort_skips_finish":  # seeded bug: early return
                out.append(("worker: returns without finish()",
                            s._replace(worker="idle", job=0)))
            else:
                out.append(("worker: finish(stopped_before_start), slot empty",
                            free(s)._replace(worker="idle", job=0)))
        elif s.worker == "recording":  # stop request, deadline or shutdown
            out.append(("worker: set_stopping()",
                        s._replace(slot="stopping", worker="stopping")))
        elif s.worker == "stopping":
            out.append(("worker: finish(finished or failed), slot empty",
                        free(s)._replace(worker="idle", job=0)))

    # ---- SIGUSR1 thread -----------------------------------------------
    if not s.sigusr1 and s.slot == "empty":
        out.append(("SIGUSR1: begin_sigusr1() claims the slot",
                    s._replace(sigusr1=True)))
    if s.sigusr1:
        out.append(("SIGUSR1: end_sigusr1() releases the slot",
                    s._replace(sigusr1=False)))
    return out


# The rules. Each must hold in every reachable state.
RULES = {
    "OneCapture: a SIGUSR1 capture never runs while a FUSE capture holds the"
    " slot or the worker runs one":
        lambda s: not (s.sigusr1 and (s.slot != "empty" or s.worker != "idle")),
    "AssertActive: while the worker runs a capture, the slot is not empty"
    " (the TRON_ASSERT(active_) in three worker methods)":
        lambda s: s.worker == "idle" or s.slot != "empty",
    "OwnJob: the capture in the slot is the one the worker runs":
        lambda s: s.worker == "idle" or s.slot == "empty" or s.slot_id == s.job,
}


def explore(variant):
    """Breadth-first search. Returns (parent map, edges)."""
    parent = {INIT: None}
    edges = {}
    queue = deque([INIT])
    while queue:
        s = queue.popleft()
        edges[s] = steps(s, variant)
        for name, t in edges[s]:
            if t not in parent:
                parent[t] = (s, name)
                queue.append(t)
    return parent, edges


def trace_to(parent, s):
    path = []
    while parent[s] is not None:
        s, name = parent[s]
        path.append(name)
    return list(reversed(path))


def show(s):
    return ", ".join(f"{k}={v}" for k, v in s._asdict().items())


def check(variant, title):
    parent, edges = explore(variant)
    n_edges = sum(len(v) for v in edges.values())
    print(f"=== {title}")
    print(f"    {len(parent)} reachable states, {n_edges} steps explored")
    failures = 0
    for rule, holds in RULES.items():
        # Dict order is discovery order, so the first bad state is a nearest one.
        bad = next((s for s in parent if not holds(s)), None)
        if bad is None:
            print(f"    PASS  {rule.split(':')[0]}")
            continue
        failures += 1
        path = trace_to(parent, bad)
        print(f"    FAIL  {rule}")
        print(f"          shortest trace, {len(path)} steps:")
        for i, name in enumerate(path, 1):
            print(f"            {i}. {name}")
        print("          state reached: " + show(bad))
    # Stuck check: from every reachable state, some list of steps must be able
    # to empty the slot again. Otherwise every later start gets "busy".
    can_empty = {s for s in parent if s.slot == "empty"}
    changed = True
    while changed:
        changed = False
        for s, outs in edges.items():
            if s not in can_empty and any(t in can_empty for _, t in outs):
                can_empty.add(s)
                changed = True
    stuck = next((s for s in parent if s not in can_empty), None)
    if stuck is None:
        print("    PASS  NeverStuck: the slot can always become empty again")
    else:
        failures += 1
        path = trace_to(parent, stuck)
        print("    FAIL  NeverStuck: the slot can always become empty again")
        print(f"          shortest trace, {len(path)} steps:")
        for i, name in enumerate(path, 1):
            print(f"            {i}. {name}")
        print("          state reached: " + show(stuck))
    deadlocks = sum(1 for outs in edges.values() if not outs)
    print(f"    states with no next step (deadlocks): {deadlocks}")
    print()
    return failures


if __name__ == "__main__":
    results = {
        "real": check("real", "The design as written in trace_capture.cpp"),
        "no_waiting_state": check(
            "no_waiting_state",
            "Seeded bug 1: take_start() leaves the state at accepted"
            " (the waiting state is removed)"),
        "start_ignores_sigusr1": check(
            "start_ignores_sigusr1",
            "Seeded bug 2: start does not test sigusr1_active_"),
        "abort_skips_finish": check(
            "abort_skips_finish",
            "Seeded bug 3: the stop-before-recording path returns"
            " without finish()"),
    }
    print("summary (failed rules per variant):", results)
    # The real design must pass, and each seeded bug must be caught.
    ok = results["real"] == 0 and all(
        n > 0 for k, n in results.items() if k != "real")
    raise SystemExit(0 if ok else 1)
