Implemented the compile-time-gated fallback allowed by
[issue #4303](https://github.com/positron-ai/tron/issues/4303).
The isolated checkout is `tron/`, on branch `fix/page-share-fuse`, based on
`ef13273ba9` (the exact #4267 head referenced in the issue). Changes are
uncommitted. `issue-4303.patch` contains the complete diff against that base.

The implementation uses the issue's defaults: six casual read-only FUSE leaves,
cumulative interval measurements by subtraction, the retained exit summary,
five scalar totals and one seven-element JSON histogram. Both binaries register
the leaves before mounting. Collection requires the CMake option ON and the
exact runtime environment value `TRON_PAGE_SHARE_COUNTERS=1`, cached on first
use. The accumulator and flush implementations and the four original test cases
are unchanged. No decision has been posted to the issue or confirmed by its
reviewer.

Validation completed:

- All six cases of `t_page_share_counters` passed: 140 assertions. This includes
  live FUSE reads without mounting, histogram ordering, read-only file metadata,
  exact runtime opt-in, and cached behavior after environment changes.
- The focused build compiles the actual test, `fuse_sysfs.cpp`, and assertion
  implementation with GCC 11.4 and locally cached dependencies. It uses no mock
  FUSE implementation or assertion bypass. See
  [build commands](validation/build-focused-test.sh),
  [build output](validation/build-focused-test.log), and
  [test output](validation/focused-test.log).
- Clang-format 19.1.7 formatting and dry-run checks pass for all five changed
  C++ files. `git diff --check` and reverse patch applicability checks pass.
- The existing `fake` test registration includes the new cases in required
  host CI. No new test binary or CI job is needed.

Validation still required on a provisioned development host:

- Full native build, `make build-test`, and `make test-host`. Native CMake
  configuration here fails because `clang++-19` is unavailable; Nix and ccache
  are also unavailable. The focused GCC test does not establish that the full
  runtron/rinzler binaries build or validate attention integration.
- Live attention runs with the environment unset, `0`, and `1`, including
  mounted FUSE reads and disabled exit-summary behavior.
- Refresh `t_page_share_counters` in `config/test-benchmarks.json` through the
  repository's Slice benchmark workflow. Its existing entry is retained.
- Whole-host same-code control and runtime-disabled comparison required by the
  issue before removing the compile-time gate. `bin/slice route` reports
  `distributed-dice`, zero cards on `claude-agentsrv`; OpenLava clients are
  unavailable. No performance records were written and no overhead acceptance
  is claimed. The CMake option remains OFF by default, preserving the production
  and benchmark builds' lack of instrumentation.

Usage and leaf semantics are documented in `tron/README.stats.md` and
`tron/README.ci.md`.
