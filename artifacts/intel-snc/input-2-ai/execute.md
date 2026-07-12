
# Consistency and Clarification Guard

When following the requirements in `input-2-ai`, the AI tool must continuously
check whether the instructions are internally consistent.

If the AI tool finds an inconsistency, ambiguity, or conflict within
`input-2-ai` that affects what it should run, measure, generate, compare, or
report, it must stop before making further project changes and request
clarification from the user.

Examples of blocking inconsistencies:

- Two files specify different test definitions, command arguments, page sizes,
  CPU sets, result filenames, or mode labels for the same test.
- A later section says to include or exclude a figure/table/test in a way that
  conflicts with an earlier section.
- A report requirement says a result must be regenerated from CSVs, but the
  tooling requirement permits hard-coded measured values.
- The expected CSV schema in the instructions does not match the script or figure
  requirements.
- A requirement says to compare SNC/3 vs SNC-OFF apple-to-apple, but another
  requirement changes page size, core set, memory placement, or command options
  between modes.
- The AI tool cannot tell whether a new instruction supersedes an older one or
  should be merged with it.

Clarification protocol:

1. Stop the current implementation or analysis before modifying code, results,
   reports, or `input-2-ai`.
2. Tell the user exactly which files/sections conflict.
3. Explain the practical consequence of the conflict.
4. Ask a concise clarification question.
5. Suggest a concrete edit that would remove the ambiguity.
6. Write any suggested edit or patch outside the source tree, preferably under
   `/tmp/input-2-ai-clarification-*`, unless the user explicitly asks to apply it.

Do not silently choose one interpretation just because it seems reasonable.
Do not edit `input-2-ai` in place while asking for clarification.

Non-blocking issues:

- Typos, spelling, or wording problems that do not change execution,
  measurement, artifact naming, or interpretation may be noted and fixed later,
  but they do not require stopping.
- Missing optional data may be handled with an explicit Todo only if the
  instructions already say that missing data should become a Todo.

The final report should include a short note for every resolved instruction
conflict that materially affected execution or interpretation.

# How to execute

The project runs once per SNC mode (SNC/3 and SNC-OFF) and is complete only when
BOTH modes have a same-machine pass. The user flips the BIOS SNC setting + reboots
between passes — the agent never changes SNC mode.

## Per-pass procedure

1. **Detect the SNC mode — and which pass this is — first.**
   `cat /sys/devices/system/node/online` (`0-5` = SNC/3, `0-1` = SNC-OFF).
   - Run the FULL applicable suite in whatever mode is live, and write its results
     into a PER-MODE SUBFOLDER — `results/snc3/` (when node/online=0-5) or
     `results/snc-off/` (0-1) — which the scripts derive from the detected mode. The
     subfolder is the authoritative mode tag (visible in `ls`, survives any tooling,
     and retro-tags files that predate any in-file column). Where a single in-file
     tag also fits (e.g. the socket-saturation CSV), use an `snc_mode` column whose
     value is `SNC3` / `SNC-OFF` — never the raw node-range string.
   - **Which pass is this? Read `results/`, NOT the SNC mode.** The mode tells you
     only *which* mode is live; it can NEVER tell you first-vs-second pass (a
     from-scratch project may start in either mode). Decide from existing data:
       - other mode's results PRESENT in `results/` → this is the **second** pass.
         That dataset is the comparison half: preserve it, use it as a prediction
         prior (step 2), and produce the full SNC/3-vs-SNC-OFF comparison now. Do
         NOT request a BIOS flip — both halves already exist.
       - other mode's results ABSENT → this is the **first** pass. Predict from
         pre-work + the math model only, report this mode, and add a Todo for the
         other-mode pass (the user will flip + reboot to collect it).
   - Intrinsically per-die tests (the mirror-die L3 rule; the 6-node DRAM sweep)
     have NO SNC-OFF form. Under SNC-OFF, run their documented analog (whole-socket
     node 0 / node 1) and note the degeneracy — do not skip silently.

2. **Predict before measuring** — (re)write `PREDICTIONS.md` for the mode about to
      be measured, BEFORE measuring it.
      - Priors: pre-work + the other mode's pass + the math model.
      - Every prediction MUST include its derivation. Do not write only the
        predicted number/range.
      - A project goal or success threshold is an acceptance criterion, not
        evidence for a predicted value.
      - For every numeric prediction, include:
        1. exact metric definition: binary/script, arguments, CPU(s), memory
           node(s), working set, access pattern, page mode, and statistic;
        2. evidence source(s): exact file path(s), row selectors, measured
           values, and whether the source is live same-machine data, pre-work
           data, or a published spec/reference;
        3. model rule/equation: the arithmetic, scaling factor, topology rule,
           or fitted constant used to transform the evidence into the
           prediction;
        4. assumptions: cache residency, SNC/NUMA topology, channel count,
           page-size/TLB expectation, core ordering, and whether the comparison
           is apples-to-apples;
        5. predicted value or range, tolerance, and confidence level;
        6. acceptance threshold, if any;
        7. falsification trigger: what measured value, ordering, plateau, or
           shape would make this prediction wrong and require gap analysis/perf.
      - For directional or qualitative predictions, include the same structure
        except that the model output may be an ordering or curve shape instead
        of a number.
      - Do not use example tables in `input-2-ai/output.md` as data unless they
        are explicitly identified as measured source data. If an example value
        motivates a sanity range, label it as an example/target, not evidence.

      Example prediction derivation style:

      Bad:

      ```markdown
      Test 1 local L3 latency: T1/read 4 MiB on cpu0/mem0 should be 35-40 ns.
      ```

      Good:

      ```markdown
      Prediction P1: local L3 latency, SNC3, cpu0/mem0, 4 MiB, read.

      - Metric: `ptr_chase --cpu 0 --mem-node 0 --size 4M --hugepage <mode> --csv`,
        median ns/load.
      - Evidence:
        - live same-machine SNC-OFF prior:
          `results/snc-off/ptr_chase_*.csv`,
          selector `phase=T1 pattern=read cpu=0 mem_node=0 size_bytes=4194304`,
          value 60.535 ns;
        - published/reference prior, if applicable:
          cite the exact article/spec and the exact values used. For example,
          a Chips and Cheese Xeon 6 article uses a weighted-average L3 topology
          model such as `(2 * 57.63 + 33.25) / 3 = 49.5 ns`. Treat those
          numbers as an example of derivation style, not reusable constants;
          a real prediction must explain why the cited data apply here.
      - Model rule:
        - Treat SNC-OFF 4 MiB L3 as an average over the three compute-die
          L3/home paths seen from cpu0.
        - With a three-die line topology, approximate those paths as local,
          one-boundary, and two-boundary:
          `SNC_OFF ~= L_local + (0 + 24 + 48) / 3 = L_local + 24 ns`.
        - Solve for the SNC3 local-die latency:
          `L_local ~= 60.535 - 24 = 36.535 ns`.
        - SNC3 cpu0/mem0 should isolate that local-die path because 4 MiB fits
          inside one SNC3 die's L3 quota.
      - Prediction: 35-40 ns, centered around 36.5 ns.
      - Tolerance: +/-10%.
      - Acceptance threshold: <=45 ns from `goal.md`; this is a pass/fail
        threshold, not evidence for the prediction.
      - Falsification:
        - >45 ns means SNC3 failed the stated L3 success target;
        - close to 60 ns means the test is not isolating local-die L3 or
          page/cache residency assumptions are wrong;
        - <30 ns would indicate a different cache level or measurement artifact.
      ```

3. **Run the tests** — on delphi-3af6; workspace root `/home/jhan/workspace/intel-vs-amd`.
      - Log in to delphi-3af6.
      - Build updated code to binaries if needed.
      - Run the tests and capture results.

Additional Test 12 execution requirement:

- After Test 11 is available for the live SNC mode, run Test 12 with the same
  core ordering and background load parameters as Test 11.
- Test 12 must produce its own CSV under the live mode subfolder:
  `results/snc3/latency_vs_socket_bw_*.csv` or
  `results/snc-off/latency_vs_socket_bw_*.csv`.
- Do not merge Test 12 rows into `socket_sat_*.csv`; Test 11 and Test 12 answer
  different questions.
- The Test 12 script should print the Test 11 background command, the selected
  saturated victim CPU, the selected remote-unused victim CPU, and the reason if
  the remote-unused victim is unavailable for a high-N point.
- When both SNC modes have data, figures and analysis must compare the two Test
  12 curves apple-to-apple. If only one mode has data, add a Todo for the missing
  mode rather than fabricating a curve.

4. **Compare each result with its prediction.** When a result disagrees:
- Analyze the gap.
- Re-run the surprise test under perf to capture perf data.
- Analyze the perf data.
- Conclude the gap between prediction and result.

## Across passes — completion & data hygiene

- The project is whole when BOTH modes have a same-machine pass.
- `results/` ACCUMULATES across passes, one subfolder per mode (`results/snc3/`,
  `results/snc-off/`) — never delete the other mode's subfolder. "Which pass is
  this" (step 1) is answered by which subfolders already contain data.
- For a clean rebuild, snapshot `results/` (or the whole `claude-workspace`) first
  so the prior pass survives.
- Tools are rebuilt from the SAME source, so the two passes stay apple-to-apple.
