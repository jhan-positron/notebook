# pr4737-review-20261001: unit tests of the PR #4737 review-response head on delphi-3bda

Short version. PR #4737 (branch jhan-amx-vnniK-i4500) got five review comments and a C++-guide note on 2026-10-01.
The answers are three commits on top of 452b2052c9. run.sh builds the new head on our half of delphi-3bda in the
VNNI build (/var/tmp/jhan/tron-i4500b) and the row-major build (/var/tmp/jhan/tron-i4500rm) and runs the unit
tests with the fake device, through exec/i4525-20260922/build2.sh. Results: exec/results/pr4737-review-20261001/
(build-r1.txt, tests-r1.txt, build-r1rm.txt, tests-r1rm.txt). Log: exec/logs/pr4737-review-20261001.log.

Words used here: VNNI K = the K cache layout of PR #4424 (TRON_K_VNNI); our half = socket 1 of delphi-3bda;
the fake device = the test build's stand-in for the FPGA; the lease = /run/lock/systems-test-ci.lease (nightly CI).
