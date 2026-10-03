# pr4737-ci-sim-20261002: the default CI's "Test host" job by hand, VNNI K on, at the PR #4737 head

Short version. The default CI builds the tests without TRON_K_VNNI (the K-layout option), so the VNNI tests of
PR #4737 never run there (review comment C1). run.sh does by hand what the "Test host" job would do with the
option on: `make build-test-host` and `make test-host` (bin/slice run --filter=host --exclude-tag=slow) inside
nix develop on our half of delphi-3bda, in /var/tmp/jhan/tron-i4500b at the PR head. Three suites: head, break
(the tail-row scores zeroed in self_attention.hpp, so the suite must fail), restored. Results in
exec/results/pr4737-ci-sim-20261002/host-suite-{head,break,restored}.txt; log exec/logs/pr4737-ci-sim-20261002.log.

Not the exact CI recipe: CI builds in a nix sandbox (nix/cmake-tron-test-build.nix) with a plugin bundle made by
three earlier jobs (up to 4 h); the make targets configure the same options (RelWithDebInfo, BUILD_NATIVE=OFF,
AVX512=ON, test + ingest models) in the dev shell with the same compiler, and run the same slice filter.
