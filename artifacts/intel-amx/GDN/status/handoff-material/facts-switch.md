# Counter switch: facts for the handoff (TRON_GDN_STATS -> TRON_ATTN_STATS)

## Short version
- At 882e5322f1 the name `TRON_GDN_STATS` stands on 13 lines in 3 files: `README.stats.md`, `h/tron/models/gdn_stats.hpp`, `t/t_gdn_stats.cpp`. All 13 lines come from the counters commit 0d69ef3ce8, so the whole switch change belongs to PR 1.
- `gdn_stats.hpp` already includes `attn_stats.hpp` and can call `attn_stats::env_enabled()`. `attn_stats.hpp` is the same blob on the model's branch, on all three commits, on PR #5022's branch and on origin/main, and the reuse does not need an edit there.
- With one switch a model without GDN layers still prints no `[gdn-stats]` line. A model with GDN layers prints both reports. The control arm `nost` of the campaign (attention counters on, GDN counters off) can no longer be run.

Line-number convention: "@882e" = at commit 882e5322f1, "@0d69" = at commit 0d69ef3ce8 (the counters commit, the source of PR 1). Read from worktree `/home/jhan/workspace/ai-runs/tron-gdn-amx` (HEAD = 882e5322f1, branch jhan-gdn-amx) with `git show` / `git grep` only.

Blob facts (`git rev-parse <commit>:<path>`):

| File | 72e1191804 | 0d69ef3ce8 | 775bba7661 | 882e5322f1 |
|---|---|---|---|---|
| `h/tron/models/attn_stats.hpp` | caf1072cd9 | caf1072cd9 | caf1072cd9 | caf1072cd9 |
| `h/tron/models/gdn_stats.hpp` | absent | a7c9f2741c | 508f1fc19b | 508f1fc19b |
| `README.stats.md` | 75eadf2043 | 37bcce1bd0 | 37bcce1bd0 | 37bcce1bd0 |
| `t/t_gdn_stats.cpp` | absent | 42e96ffdb6 | 42e96ffdb6 | 42e96ffdb6 |

- `attn_stats.hpp` is also caf1072cd9 on origin/jhan-amx-kvmul16 (ddf843ad97) and on origin/main (7eddde7895).
- `gdn_stats.hpp` is absent on origin/jhan-amx-kvmul16 and on origin/main. So PR 4 (Part B) has no part in the switch change.
- 775bba7661 changes `gdn_stats.hpp` in 2 comment hunks only: lines 23-24 and a new line 143 (@882e). So lines 1-142 have the same numbers @0d69 and @882e, and lines from 143 on are one higher @882e.
- 882e5322f1 (Part B) touches none of the four files (`git show --stat` on those paths is empty).

## 1. The two readers

| | Attention | GDN |
|---|---|---|
| Function | `tron::attn_stats::env_enabled()`, `inline bool ... noexcept` | `tron::gdn_stats::env_enabled()`, same signature |
| Lines | `attn_stats.hpp:161-172` (@882e = @72e1191804) | `gdn_stats.hpp:159-170` @882e, 158-169 @0d69 |
| Variable | `std::getenv("TRON_ATTN_STATS")`, line 163 | `std::getenv("TRON_GDN_STATS")`, line 161 @882e / 160 @0d69 |
| Read | once per process: `static const bool` set by a lambda, 162-170 | same, 160-168 @882e |
| On | exactly `"1"` (`std::strcmp`, line 165) | exactly `"1"` (line 163 @882e) |
| Unset | off, no log (line 164) | off, no log (line 162 @882e) |
| Other value | off, one `spdlog::warn`: `TRON_ATTN_STATS='{}' ignored: exactly "1" turns the attention path stats on` (166-168) | off, one `spdlog::warn`: `TRON_GDN_STATS='{}' ignored: exactly "1" turns the GDN path stats on` (164-166 @882e) |
| Only production caller | `self_attention.hpp:519` @882e, in the `self_attention::state` constructor, for every model state | `model.hpp:1758` @882e (1751 @0d69), inside `if constexpr (!gdn_operations.empty())` at `model.hpp:1732` @882e (1731 @0d69) |
| Info line when on | `attn_stats.hpp:381-384`: `attention path stats on (TRON_ATTN_STATS=1) for model '{}'{}: rows for {} app-pool workers x {} layers` | `gdn_stats.hpp:350-352` @882e (349-351 @0d69): `GDN path stats on (TRON_GDN_STATS=1) for model '{}'{}: rows for {} workers x {} operations` |
| Summary key | `"switch":"TRON_ATTN_STATS=1"`, `attn_stats.hpp:730` | `"switch":"TRON_GDN_STATS=1"`, `gdn_stats.hpp:579` @882e (578 @0d69) |

Can `gdn_stats.hpp` reuse the attention reader?
- Yes. `gdn_stats.hpp:112` (@0d69 and @882e) is `#include "tron/models/attn_stats.hpp"`.
- `gdn_stats.hpp:118-128` already imports 11 names with `using attn_stats::...;` (CLASS_LABELS, CLASS_NAMES, forward_class, inc_relaxed, is_safe_model_id, LEAF_READ_ONLY_TRUE, load_relaxed, max_relaxed, min_relaxed, N_CLASSES_2, UNSET_CYCLES_0). `env_enabled` is not in the list, because the header defines its own.
- `attn_stats.hpp` exists at 72e1191804 with the same reader (same blob; `git grep` at 72e1191804 gives `env_enabled` at line 161 and `getenv("TRON_ATTN_STATS")` at line 163).
- `std::getenv` and `std::strcmp` have no other user in `gdn_stats.hpp` (`git grep` @882e and @0d69: lines 161/163 and 160/162 only). The includes are `<cstdlib>` line 95 and `<cstring>` line 96.

## 2. Every place that names TRON_GDN_STATS at 882e5322f1

`git grep -l TRON_GDN_STATS 882e5322f1` lists 3 files. No match in `ingest/`, `src/`, any CMake file or `.github/`.

| # | File:line @882e (@0d69 if different) | What is there | What must change |
|---|---|---|---|
| 1 | `h/tron/models/gdn_stats.hpp:9-13` | Note [GDN path stats]: "Switch: the environment variable TRON_GDN_STATS ... It is separate from TRON_ATTN_STATS (...), so the attention numbers of a run do not depend on it." | Name TRON_ATTN_STATS as the switch. Delete the "separate from" sentence. |
| 2 | `gdn_stats.hpp:157-158` (156-157) | Comment over the reader: "TRON_GDN_STATS, read once per process..." | Goes away with the reader. |
| 3 | `gdn_stats.hpp:159-170` (158-169); getenv at 161 (160), warning at 164-166 (163-165) | The reader `env_enabled()` and its warning text | Delete. Use `attn_stats::env_enabled` instead (two ways, see the change list). |
| 4 | `gdn_stats.hpp:350` (349) | Info log line `GDN path stats on (TRON_GDN_STATS=1) for model ...` | Text names TRON_ATTN_STATS=1. |
| 5 | `gdn_stats.hpp:579` (578) | JSON header field `"switch":"TRON_GDN_STATS=1"` in `render_summary()` (570-585) | `"switch":"TRON_ATTN_STATS=1"`. |
| 6 | `t/t_gdn_stats.cpp:157` | `TEST_CASE("gdn-stats switch: only TRON_GDN_STATS=1 turns the stats on", "[gdn_stats]")` | Title names the new variable (or the case is dropped). |
| 7 | `t/t_gdn_stats.cpp:158` | Comment: "A run sets TRON_GDN_STATS=1 to get GDN numbers." | Same. |
| 8 | `t/t_gdn_stats.cpp:168` | `::unsetenv("TRON_GDN_STATS");` | Variable name. |
| 9 | `t/t_gdn_stats.cpp:170` | `::setenv("TRON_GDN_STATS", value, OVERWRITE_1);` | Variable name. |
| 10 | `t/t_gdn_stats.cpp:442` | `CHECK(summary.find("\"switch\":\"TRON_GDN_STATS=1\"") ...)` | Expected string follows item 5. |
| 11 | `t/t_gdn_stats.cpp:568` | `CHECK(report.find(",\"switch\":\"TRON_GDN_STATS=1\"}\n") ...)` | Expected string follows item 5. |
| 12 | `README.stats.md:306-308` | Bullet: "Collection is off unless the environment variable `TRON_GDN_STATS` is exactly `1` (read once at start). It does not depend on `TRON_ATTN_STATS`." | Rewrite: the GDN group follows TRON_ATTN_STATS. |

Related text that depends on the separate switch but does not name it:

| File:line | What is there | Note |
|---|---|---|
| `gdn_stats.hpp:68-70` (@0d69 = @882e) | "This object stores the class by itself, because the attention object stores it only when TRON_ATTN_STATS is on." | The sentence stays true. With one switch it no longer gives a reason, because both objects are then on together. Reword or keep: author's choice. The code (`current_class`, `gdn_stats.hpp:330` @882e) needs no change. |
| `gdn_stats.hpp:308-310` @882e | "False when the state was built with the switch off (model::state passes env_enabled(), tests pass a bool)." | Stays valid. |
| `t/t_gdn_stats.cpp:160-164` | "env_enabled() reads the variable once per process ... No case of this binary calls env_enabled() in the test process itself" | Still holds for `attn_stats::env_enabled`: `git grep env_enabled 882e5322f1` finds no call in `t/t_gated_delta_net.cpp`, the other source of this binary (`t/CMakeLists.txt:269-272`), and that file has no `attn_stats`, `self_attention` or `model::state`. |
| `t/t_gdn_stats.cpp:172` | Unqualified `env_enabled()`, resolved through `using namespace tron::gdn_stats;` at line 32 | Must still resolve after item 3. |
| `t/t_gdn_stats.cpp:63` | `constexpr int OVERWRITE_1 = 1;` used only at line 170 | Unused if the test case is dropped. |
| Commit message of 0d69ef3ce8 | Subject "Add GDN path statistics (TRON_GDN_STATS)"; body lines "The environment variable TRON_GDN_STATS turns collection on ... does not depend on TRON_ATTN_STATS." | Rewrite when PR 1 is made. The messages of 775bba7661 and 882e5322f1 name neither switch. |
| PR #5572 body, line 138 (`gh pr view 5572`: open, draft, head 882e5322f1) | "In control runs on 3 cells, `TRON_GDN_STATS=1` changes the time to first token by -0.2 to +0.3 % and decode by -0.5 to 0.0 % ..." | Names the old switch. See section 4 for what that control measured. |

Places checked that do NOT name the switch:
- `ingest/src/TronCpp.hs:3145-3146` @882e: the generated call passes `outer_state.gdn_path_stats.get()`. No switch name.
- `t/CMakeLists.txt:266-272`: names `t_gdn_stats.cpp` only.
- `model.hpp:1368-1373`, `2155-2165` @882e and `gdn_execution.hpp:125-128`: comments say "the switch" without a name.
- `TRON_ATTN_STATS` @882e stands in `README.stats.md:247,308`, `attn_stats.hpp:8,159,163,167,382,730`, `gdn_stats.hpp:12,69`, `t/heterogeneous_scheduler_compile.cpp:356`, `t/t_attn_stats.cpp:553`, `t/t_llama_unit.cpp:3276`. None of these needs a change for the reuse except the two `gdn_stats.hpp` lines and README line 308.

Test coverage facts:
- `t/t_attn_stats.cpp` has no `setenv`, `unsetenv` or `env_enabled` (`git grep` @882e). So the case at `t/t_gdn_stats.cpp:157-181` would be the only value test of the shared reader if it is kept with the new name.
- No test checks that `gdn_path_stats->enabled` follows the reader (`git grep gdn_path_stats 882e5322f1` gives `model.hpp` and `TronCpp.hs` only). The attention side has such a check at `t/t_llama_unit.cpp:3279-3280`.

## 3. What is printed, and where

| | Attention | GDN |
|---|---|---|
| Exit report trigger | `~model_stats()`, `attn_stats.hpp:388-390`: `if (enabled) print_report(stderr);` | `~model_stats()`, `gdn_stats.hpp:356-358` @882e, same |
| Guard | `attn_stats.hpp:816-828`: returns when off, or when no forward and no visit was counted | `gdn_stats.hpp:643-651`: returns when off, or when no forward and no GDN job was counted |
| Lines | `[attn-stats] model <id>: <summary JSON>` (829-830). Per class: `totals` (832), `forwards` (834), `k_tokens per layer (amx/avx/fpga)` (846). 7 lines for 2 classes. | `[gdn-stats] model <id>: <summary JSON>` (652-653). Per class: `totals` (655), `forwards` (657), `wall_cycles per op` (673), `head_tokens per op (token/chain/amx)` (675), `per worker (busy_cycles/head_tokens)` (690). 11 lines for 2 classes. |
| FUSE path | `/model/<id>/attention/`, or `attention_eagle/` for an EAGLE draft state (`attn_stats.hpp:918-919`) | `/model/<id>/gdn/`, or `gdn_eagle/` (`gdn_stats.hpp:744-745`) |
| Leaves always | `summary`, `<class>_totals`, `<class>_forwards` (934-939) | same three (758-763) |
| Leaves only when on | `<class>_layer_<L>`, `<class>_worker_<W>` (940-948) | `<class>_op_<I>`, `<class>_worker_<W>` (764-772) |

- Measured line counts agree: log `exec/results/gdn-impl-20261121/rt/logit-q35-tp4-1u-p1024__base__rep1.log` has 7 `[attn-stats]` lines and 11 `[gdn-stats]` lines.
- In that log the `[gdn-stats]` block (log lines 173-183) comes before the `[attn-stats]` block (185-191). `gdn_path_stats` is declared after `self_attn_state` (`model.hpp:1367`, `1373` @882e).

Does a model without GDN layers print any `[gdn-stats]` line under the shared switch? No.
- The only production construction of `gdn_stats::model_stats` is `model.hpp:1757-1759` @882e, inside `if constexpr (!gdn_operations.empty())` at `model.hpp:1732`.
- `gdn_operations` is an empty array when the plugin declares none (`model.hpp:697`, `736-741` @882e).
- So `gdn_path_stats` stays null in such a state (`model.hpp:1368-1373`). There is no object, so no destructor report, no info line, and no `/model/<id>/gdn/` leaf (`register_fuse_files` at `model.hpp:1760` is in the same block).
- `forward()` leaves the optional scope empty (`model.hpp:2161-2165` @882e).
- The only callers of `print_report` outside tests are the two destructors (`git grep print_report 882e5322f1`).
- Basis: code reading. Not verified by a run: no log of a model without GDN layers with a GDN switch set was read.

Does a model with GDN layers get the attention stats turned on too? Yes.
- `self_attention.hpp:519` @882e builds the attention object with `attn_stats::env_enabled()` in every model state. Qwen3.5 4B has attention layers, so the same variable turns both objects on.
- The campaign already ran that way. Its 6 main arms set both variables (`exec/gdn-impl-20261121/campaign.sh:34-40`). The sample log shows both info lines: "attention path stats on ... rows for 55 app-pool workers x 32 layers" (log line 156) and "GDN path stats on ... rows for 56 workers x 24 operations" (log line 159).
- Memory when on, by the formulas in the header comments with those dimensions: attention rows 2 x 55 x 32 x 192 bytes = 675,840 bytes plus 2 x 32 x 64 = 4,096 bytes of timers (`attn_stats.hpp:83-84`); GDN rows 2 x 56 x 24 x 128 bytes = 344,064 bytes (`gdn_stats.hpp:87-88`). The struct sizes are taken from the comments, not checked with `sizeof`.
- Run-time cost of the attention counters on this model: Insufficient data. Every runtron arm in the two script folders sets `TRON_ATTN_STATS=1` (see section 4). A pair of runs with no stats variable versus `TRON_ATTN_STATS=1` would give it.
- Off state: unchanged. The attention hooks and the GDN hooks each test one bool (`attn_stats.hpp:12-17`, `gdn_execution.hpp:125-128`).

## 4. Measurement scripts (outside the repository)

Folder `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/`: 0 lines match `TRON_GDN_STATS`, `GDN_STATS` or `gdn-stats` (`grep -rn`, all subfolders). Its scripts use `TRON_ATTN_STATS=1` only (`run-one.sh:28` default `ARMENV`, `campaign.sh:26-27`, `trace.sh:41`) and parse `[attn-stats]` only (`collect.py:38,41`, `run-one.sh:81`).

Folder `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/`:

| File:line | What the line does |
|---|---|
| `campaign.sh:10` | Comment: every arm sets both variables. |
| `campaign.sh:17` | Comment: arm `orig` (base build) ignores TRON_GDN_STATS. |
| `campaign.sh:18` | Comment: arm `nost` = counter build with TRON_GDN_STATS unset. |
| `campaign.sh:34` | Sets `STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"`, used by arms at lines 35-41. |
| `campaign.sh:42` | Arm `nost|ctr|TRON_ATTN_STATS=1`: the control with the GDN counters off (no TRON_GDN_STATS). |
| `token-check.sh:20` | Sets the same `STATS`, used by arms at lines 22-32. |
| `logit-margin.sh:27` | Sets the same `STATS`, used by arms at lines 28-31. |
| `build.sh:84` | Echoes the count of `TRON_GDN_STATS` literals in `gen/runtron` (report only, no pass/fail test on that count). |
| `collect.py:7-8` | Docstring: names both tags and both variables. |
| `collect.py:55` | Loop over tags `attn-stats` and `gdn-stats`; lines 56-61 parse the summary, totals and forwards JSON of each. |
| `collect.py:62` | Parses `[gdn-stats] ... wall_cycles per op`. |
| `collect.py:65` | Parses `[gdn-stats] ... head_tokens per op (token/half or chain/amx)`. |
| `collect.py:69` | Parses `[gdn-stats] ... per worker (busy_cycles/head_tokens)`. |
| `gen_pr_body.py:331` | Template of the PR-body sentence on the cost of `TRON_GDN_STATS=1`. |
| `pr-body.md:138` | The generated sentence (same text as PR #5572 body line 138). |
| `gen_report.py:709, 743, 759` | Report text: "TRON_GDN_STATS=1 turns them on". |
| `gen_report.py:790` | Arm table row `nost`: "TRON_GDN_STATS not set". |
| `gen_report.py:832-833` | Report text: 6 arms have both sets of counters on; the two control arms have the attention counters only. |
| `gen_report.py:1295` | Builds a sample `[gdn-stats] ... totals` line for the report. |

- `understand/` in the same folder holds 81 more matching lines in 9 record files (JSON and markdown outputs of earlier workflow steps, not scripts): implement-stats.json 19, pre-pr-check-result.json 18, verify-page-v2-result.json 17, verify-page-result.json 7, stats.report.md 5, stats.facts.md 4, review-findings-raw.json 4, review-result.json 4, verify-decode-section-result.json 3. They are not listed line by line here.
- `e4b-check.sh:29-31` sets `TRON_ATTN_STATS=1` only and parses `[attn-stats]` only (line 69).
- No script in the two folders reads the summary key `switch` (the `"switch"` matches in `gen_pr_body.py`, `report_data.py`, `gen_report.py` are a column of the unit-test table).
- The `[gdn-stats]` tag and its line formats do not change with the switch reuse, so the parser lines of `collect.py` keep working.

What the shared switch does to the measured control:
- Arm `nost` ran build `ctr` with `TRON_ATTN_STATS=1` and no `TRON_GDN_STATS`. Its 9 logs exist under `exec/results/gdn-impl-20261121/rt/` (for example `q35-tp4-1u-p1024__nost__rep21.log`: 7 `[attn-stats]` lines, 0 `[gdn-stats]` lines, attention info line present, GDN info line absent).
- So the sentence at `pr-body.md:138` is the cost of the GDN counters on top of the attention counters, measured at 0d69ef3ce8. After the change this state (attention on, GDN off) cannot be produced. The numbers stay valid for 0d69ef3ce8 only.
- Every arm that sets `TRON_GDN_STATS=1` also sets `TRON_ATTN_STATS=1` through `STATS`. So a re-run on the new code still gets both reports. The extra `TRON_GDN_STATS=1` would then be read by nothing.

## 5. README.stats.md at 882e5322f1 (same blob at 0d69ef3ce8)

- There is no heading for either switch. Both groups are prose inside section "## How to add a FUSE stat" (heading at line 228), before "### 1. Register the leaf" (line 410).
- Attention group: one paragraph, lines 242-298. The switch sentence is lines 246-250 ("Collection is off unless the environment variable `TRON_ATTN_STATS` is exactly `1` (read once at start) ...").
- GDN group: lines 300-367, added by 0d69ef3ce8 (diff hunk `@@ -297,6 +297,75 @@`). Intro 300-304 ("A second casual group ... It follows the rules of the attention group:"), rule bullets 306-324, key list 326-367.
- The GDN switch is described at lines 306-308 only. Lines 309-311 (off state) and 312-317 (on state, the `[gdn-stats]` report) say "the switch" without a name and stay valid.
- So the GDN text already sits directly after the attention text. Nothing has to move. Only the bullet at 306-308 changes.
- Two more GDN lines from the same commit need no change: the tree table row `/model/<model_id>/gdn/` at line 422 and "the `model::state` constructor for `h/tron/models/gdn_stats.hpp`" at line 429.

## Minimal change list (all in PR 1, built from 0d69ef3ce8)

Line numbers @0d69, with @882e in brackets where different.

1. `h/tron/models/gdn_stats.hpp:156-169` [157-170]: delete the comment and the function `gdn_stats::env_enabled()`. Take the attention reader instead, in ONE of two ways:
   - (i) add `using attn_stats::env_enabled;` to the using-list at lines 118-128. Then `model.hpp:1751` [1758] (`gdn_stats::env_enabled()`) and `t/t_gdn_stats.cpp:172` (`env_enabled()`) need no edit.
   - (ii) change `model.hpp:1751` [1758] to `attn_stats::env_enabled()` and qualify the call at `t/t_gdn_stats.cpp:172`.
   - Way (i) edits one file fewer. Neither way was compiled.
2. `gdn_stats.hpp:95-96`: drop `<cstdlib>` and `<cstring>` if no other user remains (grep finds `getenv` and `strcmp` only in the deleted reader).
3. `gdn_stats.hpp:9-13`: Note text names TRON_ATTN_STATS as the switch; delete "It is separate from TRON_ATTN_STATS ..., so the attention numbers of a run do not depend on it."
4. `gdn_stats.hpp:349` [350]: info log text `(TRON_GDN_STATS=1)` -> `(TRON_ATTN_STATS=1)`.
5. `gdn_stats.hpp:578` [579]: `"switch":"TRON_GDN_STATS=1"` -> `"switch":"TRON_ATTN_STATS=1"`.
6. `t/t_gdn_stats.cpp:442` and `:568`: expected `switch` strings follow item 5.
7. `t/t_gdn_stats.cpp:157, 158, 168, 170`: the switch test case names TRON_ATTN_STATS (title, comment, `unsetenv`, `setenv`).
8. `README.stats.md:306-308`: the bullet says that GDN collection follows `TRON_ATTN_STATS`; delete "It does not depend on `TRON_ATTN_STATS`."
9. Commit message of the counters commit: subject "(TRON_GDN_STATS)" and the two body lines on the switch.
10. PR text: the sentence of `pr-body.md:138` (source `gen_pr_body.py:331`, live in PR #5572 body line 138) names `TRON_GDN_STATS=1`.

Open choices for the author (not edits I can call required):
- `gdn_stats.hpp:68-70`: keep or reword the reason for the object's own class store.
- Keep the switch test case with the new name (item 7), or drop it. If dropped: `t/t_gdn_stats.cpp:63` (`OVERWRITE_1`) becomes unused and the header comment at `t/t_gdn_stats.cpp:2` lists "the switch".
- `attn_stats.hpp:166-168` (warning text) and `attn_stats.hpp:8-17` (Note) speak of the attention stats only. The reuse works without touching them. Touching them would change a file that is byte-identical on origin/main, the model's branch and PR #5022's branch.

Scripts outside the repository, only if a campaign is re-run: `campaign.sh:34`, `token-check.sh:20`, `logit-margin.sh:27` (`STATS`), `build.sh:84` (literal count), `campaign.sh:42` and `gen_report.py:790, 832-833` (arm `nost`, which has no equivalent any more).

## Not verified
- No build and no test run. Whether way (i) or (ii) compiles, and whether `<cstdlib>` / `<cstring>` can be dropped, rest on `git grep` only.
- Whether the PR 2 / PR 3 hunks of 775bba7661 in `gdn_stats.hpp` (lines 23-24 and 143 @882e) rebase without conflict onto the edited PR 1. The nearest edited lines are 9-13, the using-list 118-128 and the reader 156-169; no rebase or `git merge-tree` was run.
- "No `[gdn-stats]` line for a model without GDN layers": code reading only, no log.
- Run-time cost of `TRON_ATTN_STATS=1` on Qwen3.5 4B: Insufficient data (no arm without it).
- The row sizes 192 bytes and 128 bytes come from header comments, not from `sizeof`.
