## Short version

Line 20 of `go.sh` now holds your text. The change is in the local file only: no command of this work ran on CRB (the Arm reference server), so the new message is not in effect there. The edit has two side effects in the local folder: `go.sh` no longer matches the checksum list of 2026-11-17, and the facts sheet of that run cannot be rebuilt in this folder until line 20 is put back.

## The change

```diff
- [ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"
+ [ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"
```

- File: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`, line 20. No other line changed.
- Test [Ref1]: a copy of the script, started with the marker file present, prints its pid line, then `FAILED: RUNNING file present, Jeremy or someone else is using CRB`, then one state line. It ends with status 1. The syntax check `bash -n` passes.

## What follows from the edit

1. **CRB still has the old line.** Your `manual-run/run.sh` builds `go-direct.sh` from the `go.sh` that is on CRB. By the last record (2026-11-17) that copy has the old line 20. So a run started today would still print the old message.
2. **Do not copy `go.sh` alone.** Line 4 of `run.sh` compares the scripts on CRB with the checksum list on CRB. With only the new `go.sh` there, it prints `NOT STARTED: a script differs from local.sha` and ends with status 4 [Ref3]. A copy needs a fitting list on CRB as well. A copy also needs a login to CRB, which I do not do without your go-ahead.
3. **The new text is rarely printed.** `run.sh` tests the marker file itself first and prints `RUNNING file present: stop`. When the file appears during a run, `ra.sh` or `rx.sh` stops with its own message, and `go.sh` then prints `FAILED: ra.sh session N rc 3` or `FAILED: rx.sh NAME rc 3`. Line 20 prints its message only when the file exists at the moment line 20 runs.
4. **`go.sh` no longer matches `local.sha`.** `local.sha` is the checksum list written at the start of the run of 2026-11-17. I did not change it, because it is the record of what ran. `sha256sum -c local.sha` now prints `go.sh: FAILED`. This is expected. Please do not write `local.sha` again: the facts sheet tests the scripts against it and prints its file time.
5. **The proof of the old run is kept.** With the old line 20 put back, the text of `go.sh` has the listed checksum again [Ref1]. The list generator `make_list.py` tests this at every build. It stops when `go.sh` or `local.sha` changes.
6. **The facts sheet cannot be rebuilt in this folder now.** `build_facts.py` compares the run scripts with `local.sha` (its check 20). It then stops and writes nothing. In a copy of the folder with the old line 20 it passes all 27 checks, and it writes the same sheet [Ref2]. The stored `FACTS.md`, `facts.json` and the report page are unchanged. The list build needs the new line 20. So the two builds need opposite states of `go.sh`.
7. **`go2.sh` keeps the old message** in lines 16 and 25. You named `go.sh` only.

## What else changed

- **28 files changed in content:** `go.sh`, 12 inputs of the explanation files, 9 rebuilt explanation files (among them `go.sh.md` and `local.sha.md`), 3 hand-written explanation files, the list generator, the agent briefing, and the list (7 new lines, 3 changed lines).
- **One new folder** holds the tests of this edit and a byte copy of `go.sh` as it ran on 2026-11-17: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24/`.
- **Not changed:** `local.sha`, `go2.sh`, `ra.sh`, `rx.sh`, your `run.sh`, the stored facts sheet and report, all 44 data explanation files, and everything on CRB.
- My memory notes record the state. The boot-id task of 2026-11-22 is still open: lines 15, 16 and 26 of `go.sh` are unchanged.

## How this was checked

- Three kept tests pass: 9 checks [Ref1], 8 checks [Ref2] and 12 checks [Ref3].
- `companion_tool.py verify-all` confirms for all 33 code explanation files that the left column equals the source. `make_list.py --check` passes.
- Independent checker agents read every new sentence against the files in three rounds. I corrected what they found. The last round found no false statement.

## Decisions that are yours

- Copy the edited `go.sh` to CRB now, or together with the boot-id change later.
- Accept that the facts sheet rebuilds only in a copy with the old line 20, or have check 20 read a kept copy of the scripts as they ran.
- Give the other marker messages the same wording or not: `run.sh` line 2, `go2.sh` lines 16 and 25, `ra.sh` line 12, `rx.sh` lines 7, 13 and 19. A change of `ra.sh` or `rx.sh` also changes a checksum that the run scripts test.

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24/check_line20.py`, output `check_line20.out`.
- [Ref2] `check_facts_build.py` in the same folder, output `check_facts_build.out`.
- [Ref3] `check_start_command.py` in the same folder, output `check_start_command.out`. It runs the text of your `manual-run/run.sh` without ssh, with fake programs, for three states of the folder on CRB.
