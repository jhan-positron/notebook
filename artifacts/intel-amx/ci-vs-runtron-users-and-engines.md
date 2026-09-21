# CI versus runtron: total users and engine layout

Recorded: 2026-09-21. This note is maintained directly in the notebook repository.

## Short version

Whole-machine nightly CI runs 4 TP2 engines or 2 TP4 engines on 8 accelerator cards.
Our earlier runtron campaigns launch one engine inside the available 4-card half machine.
The tables below distinguish total users from users per engine for both setups.

## Terms and scope

- **CI**: continuous integration; here, the nightly system performance tests on
  `delphi-3bda`, the 8-card test server.
- **runtron**: Tron's command-line inference tool.
- **rinzler**: Tron's model-serving server, used by the nightly tests.
- **Engine**: one model-serving process, with its own group of accelerator cards.
- **TP2 / TP4**: tensor parallelism across 2 / 4 accelerator cards within one
  engine. Those cards cooperate on the engine's users.
- **Total users**: concurrent users across all engines in the specified run.
- **Users per engine**: concurrent users assigned to one engine.
- **Caddy**: the nightly server's request proxy. Its `least_conn` policy routes
  requests toward the engine with the fewest active connections.

This comparison uses the nightly engine layout recorded in the September 2026
handoffs and the single-process runtron setup in our earlier campaigns.
It does not describe every possible CI or runtron configuration.
[[Nightly layout](../../handoffs/claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md),
[runtron campaign](exec/vnnik2-20260915/campaign.sh)]

## Comparison for 2, 4, 8, 16 and 32 total users

Each bracket lists **users on each engine**. For example, `[1, 1, 0, 0]`
means 4 running engines: 2 serve one user each, and 2 serve no users.
The order of entries does not identify particular physical engines.

| Total concurrent users | CI whole machine, TP2: 4 engines | CI whole machine, TP4: 2 engines | runtron half machine, TP2: 1 engine | runtron half machine, TP4: 1 engine |
|---:|---|---|---|---|
| **2 users** | **[1, 1, 0, 0]** | **[1, 1]** | **[2]** | **[2]** |
| **4 users** | [1, 1, 1, 1] | [2, 2] | [4] | [4] |
| **8 users** | [2, 2, 2, 2] | [4, 4] | [8] | [8] |
| **16 users** | [4, 4, 4, 4] | [8, 8] | [16] | [16] |
| **32 users** | [8, 8, 8, 8] | [16, 16] | [32] | [32] |
| **Cards assigned to these engines** | **8 cards** | **8 cards** | **2 cards** | **4 cards** |

The CI columns are **calculated balanced shapes**, assuming healthy engines and
overlapping requests. They are not new measurements of Caddy's routing.
The runtron columns assume one process with `--users N` and no additional prompt
inputs or overrides. Runtron adds those users to that process's prompt list.
[[runtron.cpp at commit 30c4ac82cb, lines 734-742](https://github.com/positron-ai/tron/blob/30c4ac82cbb6959f7e4f66b29efb36f5e0749b48/src/runtron.cpp#L734-L742)]

The arithmetic is: divide the total users by the number of engines, then
distribute any remainder one user at a time. This produces the nominal balanced
allocation. In particular, 2 total users over 4 engines means `[1, 1, 0, 0]`,
not an actual half-user on every engine.

**Insufficient data for the exact live assignment of a new 2-user CI run.**
Per-engine active-request records during that run would establish the actual
distribution. The prior handoffs establish the engine layout and the earlier
8-user comparison.
[[Earlier question and answer](../../handoffs/claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)]

## The 2-total-user case

```text
CI TP2:   user A -> engine A    user B -> engine B
          engine C: idle       engine D: idle

CI TP4:   user A -> engine A    user B -> engine B

runtron:  users A + B -> one engine
```

This diagram shows the balanced reference allocation from the table.
An idle CI engine still owns its assigned cards. "Idle" here means it has no
user request in this example.

## What "runtron on half the machine" means

A half-machine allocation makes 4 cards available. It does not automatically
create enough runtron processes to use them all.

- **One TP2 runtron engine** uses 2 cards. The other 2 cards in the half machine
  are unused by that run.
- **One TP4 runtron engine** uses all 4 cards in the half machine.
- In the recorded launcher, TP2 selects `--instance 2,4` with 2 explicit devices.
  TP4 selects `--instance 1,2` with 4 explicit devices. The launcher invokes one
  runtron process for each test run.
  [[Campaign placement and invocation, lines 69-72 and 183-198](exec/vnnik2-20260915/campaign.sh)]

To fill the half machine at TP2, launch **two runtron engines** on separate
2-card groups and divide the total users explicitly:

| Total concurrent users | Two TP2 engines: users on each engine | `--users` for each process | Cards assigned |
|---:|---|---:|---:|
| 2 users | [1, 1] | 1 | 4 cards |
| 4 users | [2, 2] | 2 | 4 cards |
| 8 users | [4, 4] | 4 | 4 cards |
| 16 users | [8, 8] | 8 | 4 cards |
| 32 users | [16, 16] | 16 | 4 cards |

This is a different setup from the single-process runtron columns above.
For example, two processes each using `--users 2` produce **4 total users**.
The earlier half-machine server campaign records the two separate TP2 device
groups that fit this allocation.
[[Two-engine placement](exec/p0perf-20260913/rz.sh)]

## How to read the earlier handoffs

The earlier nightly comparison used **8 total users**:

- Nightly TP2: 4 engines, approximately 2 users per engine.
- Nightly TP4: 2 engines, approximately 4 users per engine.
- Our single-engine runs: 8 users on one engine.

Thus, the earlier phrase "2 users per engine" did not describe a run with
2 total users.
[[September 12-13 comparison](../../handoffs/claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md),
[September 18 follow-up question](../../handoffs/claude_20260918_pr3879-amx-ci-harness-run.md)]

These tables describe user placement and card allocation. They do not predict
throughput or latency. No new inference workload was run to prepare this note.
