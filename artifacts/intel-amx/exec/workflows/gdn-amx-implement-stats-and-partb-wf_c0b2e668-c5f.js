export const meta = {
  name: 'gdn-amx-implement-stats-and-partb',
  description: 'Two implementers in separate worktrees: GDN counters (base build) and AMX attention kernels for 256-wide heads (Part B), each built and unit-tested on delphi-3b35',
  phases: [{ title: 'Implement', detail: 'counters agent and Part B agent, in parallel' }],
}
const U = '/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/understand'
const COMMON = `
You are an implementer on the GDN/AMX project for tron (an LLM inference program, C++). Work alone, end to end: write the code, build it, run the unit tests, fix what fails, commit. Do not stop at a plan.

Shared facts
- Base commit: 72e1191804ecb7591b23230439786a6a1ca784b8 (head of the open pull request that adds the model Qwen3.5 4B: 24 GatedDeltaNet (GDN) layers + 8 full-attention layers with 16 query heads x 256 values and 4 KV heads).
- The design: /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/design.txt (plain text of GDN/gdn-amx-design.html; sections 5 and 6).
- Reader reports made today from the base commit (file:line anchors, traps, proposals). Read the ones named in your task BEFORE writing code: ${U}/stats.report.md, gdnpath.report.md, gdntests.report.md, attnshape.report.md, proto.report.md, bench.report.md, and next to each a .facts.md file with key facts and traps. Verify an anchor before you rely on it.
- A read-only worktree of the base commit for reference: /home/jhan/workspace/ai-runs/tron-qwen35-4b. Never edit it.

Rules for the code
- Follow the repository's own rules (AGENTS.md, t/AGENTS.md) and the user's C++ rules: load the skill "cpp-coding-guide" with the Skill tool before writing C++ and follow it. Comments are plain English: one claim per sentence, no idioms, terms from outside the code defined at first use. Never write a pull-request or issue number, a reviewer name or review-round narration in source. Do not use these words anywhere: convoy, refund, "in disguise", swept.
- Surgical changes: touch only what the task needs. Do not reformat or "improve" neighbouring code. Do not change the instruction order of existing kernels.
- Format every C++ file you touch with clang-format 19.1.7: "uvx --from clang-format==19.1.7 clang-format -i <files>" run from the worktree root (the repo has a .clang-format). Check "git diff --check".
- Commit on your branch only, with "git -C <worktree> commit --no-verify" (no lefthook on this machine). Stage files by name; never "git add -A". Never push. Never run "git worktree prune" or "git gc" on the shared repository. Do not create or delete worktrees. End every commit message with the line: Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
- Do not put a real model slug string (such as the Qwen3.5 slug) into a test source: a configure-time audit rejects it.

Rules for the machines
- This agent machine (agentsrv): shell commands are pinned to 6 CPUs. Do not build tron here. Do not run more than 6 busy processes. Do not use "cd" in shell commands (a hook prints a directory listing); use absolute paths and "git -C".
- Builds and tests run on the server delphi-3b35 through ssh ("ssh -o BatchMode=yes delphi-3b35 '<command>'", user jhan; the home directory and /home/jhan/workspace are the same NFS files on both machines). It is a SHARED machine. Other users hold the first CPU socket and the first half of the FPGA cards. Rules there: use only CPUs 96-143; never touch a process of another user; do not read other users' home directories; no sudo; do not run runtron or anything that opens an FPGA card (the lead runs those); inside ssh do not use "cd" without need and never "pkill -f" with a pattern that matches your own command line.
- Build with the campaign script, which checks out your commit into a server-local tree /var/tmp/jhan/b35-gdn-<TAG> and builds incrementally on CPUs 96-135:
    ssh -o BatchMode=yes delphi-3b35 'TAG=<TAG> SHA=<commit> TARGETS="<targets>" bash /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/build.sh; cat /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/build-<TAG>.done; tail -40 /home/jhan/workspace/intel-AMX/exec/logs/gdn-impl-20261121-build-<TAG>.log'
  The first build of a tag takes 10 to 20 minutes (it exports the model and builds everything); later builds are incremental. Use a long ssh timeout (the Bash tool allows 600000 ms; if a build needs longer, start it with "nohup ... >/dev/null 2>&1 &" inside ssh and poll the .done marker with separate short ssh calls). The script builds only COMMITTED code: commit work-in-progress freely on your branch, and squash into clean commits at the end (git reset --soft <base> && git commit).
  The build uses a one-model registry (only Qwen3.5 4B). A test target whose model requirement is not in that registry is not generated. If a target you need is missing in that tree, say so in your report rather than changing the registry.
- Run a unit test on the server from the build tree root, pinned to our CPUs, for example:
    ssh -o BatchMode=yes delphi-3b35 'cd /var/tmp/jhan/b35-gdn-<TAG> >/dev/null && SYSTEM_CONFIG="--instance 1,2" taskset -c 96-135 ./gen/<test> 2>&1 | tail -30'
  The server CPU has AMX, so AMX kernel test cases really execute there. A case that prints a "skip" warning has not run: treat that as a failure of your verification.
- Keep every temporary file under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/<your key>/ on this machine, or under /var/tmp/jhan/gdn-impl-<your key>/ on the server.

Your final answer is data for the lead engineer, not a message to a user. Be exact. Report failures and skipped checks plainly; never say a test passed that you did not run.`
const SCHEMA = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    worktree: { type: 'string' },
    head_commit: { type: 'string', description: 'full sha of the final commit on the branch' },
    commits: { type: 'array', items: { type: 'object', properties: { sha: { type: 'string' }, subject: { type: 'string' } }, required: ['sha', 'subject'] } },
    files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: 'what was built, design decisions and deviations from the brief, with file:line anchors' },
    interface_notes: { type: 'string', description: 'exact signatures, struct fields, env variable names, output formats that other code and scripts must match' },
    verification: { type: 'array', items: { type: 'object', properties: { check: { type: 'string' }, command: { type: 'string' }, result: { type: 'string' } }, required: ['check', 'result'] } },
    not_done: { type: 'array', items: { type: 'string' } },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['branch', 'worktree', 'head_commit', 'commits', 'files_changed', 'summary', 'interface_notes', 'verification', 'not_done', 'risks'],
}
const STATS = `
YOUR TASK (key: stats): the GDN counters, as the first commit of the series ("the base build holds the counters").
Worktree: /home/jhan/workspace/ai-runs/tron-gdn-stats, branch jhan-gdn-stats (already created at the base commit). Build tag: stats. Benchmark CPU if you need one: 141.
Read first: ${U}/stats.report.md (all of it; section 10 is the agreed design and the list of hook points), ${U}/stats.facts.md, ${U}/gdnpath.facts.md, ${U}/gdntests.facts.md.

Build exactly the design of section 10 of stats.report.md: new header h/tron/models/gdn_stats.hpp (namespace tron::gdn_stats, Note [GDN path stats]), environment switch TRON_GDN_STATS (exactly "1" turns it on, read once, same rule and warning style as TRON_ATTN_STATS), one model_stats object per model state owned by model::state as std::shared_ptr member gdn_path_stats, FUSE leaves under /model/<id>/gdn (casual leaves, same rules as the attention leaves), the "[gdn-stats]" exit report on stderr, a forward_scope at the site of the attention forward scope, the new last parameter of run_gdn_operation (gdn_stats::model_stats* stats = nullptr), the generator edit in ingest/src/TronCpp.hs (gdnExecutionCall passes outer_state.gdn_path_stats.get()), README.stats.md text, a new test file t/t_gdn_stats.cpp as a second FILES entry of the t_gated_delta_net target, and a hook test in t/t_gated_delta_net.cpp that passes an enabled object through run_gdn_operation.

Fixed interface (other engineers write the chain path and the AMX block path against it in parallel; do not rename these):
  namespace tron::gdn_stats {
  enum class gdn_path : uint8_t { token = 0, column_half = 1, amx_block = 2 };
  inline constexpr size_t N_PATHS_3 = 3;
  inline constexpr const char* PATH_NAMES[N_PATHS_3] = {"token", "half", "amx"};
  // Stack tally of one run_gdn_operation call (one worker, one operation). Plain integers.
  struct work_tally {
    uint64_t items = 0;                          // (chain, key head) work items
    uint64_t head_tokens[N_PATHS_3] = {};        // tokens per path, counted once per key head
    uint64_t amx_blocks = 0;                     // value-head blocks of 32 tokens that the AMX block kernel finished
    uint64_t amx_fallback_blocks = 0;            // value-head blocks that the AMX block kernel refused (not finite); they ran the column-half kernel
    uint64_t half_full_block_tokens = 0;         // column-half tokens inside full blocks on the grid (the volume the AMX path would take)
    uint64_t start_cycles = 0;                   // bind, zero or copy from the source, NaN check
    uint64_t pre_cycles = 0;                     // per-token work before the recurrence (chain path): convolution, normalization, decay, beta
    uint64_t copy_cycles = 0;                    // reserved for state layout copies of the chain path
    uint64_t recurrence_cycles[N_PATHS_3] = {};  // token: the whole step() loop; half; amx
    uint64_t post_cycles = 0;                    // per-token work after the recurrence (chain path): norm and output gate
    uint64_t write_cycles = 0;                   // write_checkpoint
  };
  }
In this commit only the token path exists: every chain adds chain.order.size() to head_tokens[token], the time of the step() loop to recurrence_cycles[token], and the start and write times. The other fields stay zero but must be rendered in the JSON (so that the scripts see one format in every build): use the JSON key names items, token_head_tokens, half_head_tokens, amx_head_tokens, amx_blocks, amx_fallback_blocks, half_full_block_tokens, start_cycles, pre_cycles, copy_cycles, token_recurrence_cycles, half_recurrence_cycles, amx_recurrence_cycles, post_cycles, write_cycles, gdn_jobs, busy_cycles in the totals, op and worker leaves and in the "[gdn-stats] <class label> totals:" line. Per operation also wall_cycles, wall_max_cycles, wall_count (the GDN wall of one operation of one forward = last worker exit minus first worker entry, as section 10 defines it). The forwards record has forwards, wall_cycles, wall_max_cycles, token_jobs, chains, n_gdn_workers_min, n_gdn_workers_max. The exit report must also print, per class, the line "[gdn-stats] <class label> wall_cycles per op: 0=<sum> 1=<sum> ..." and "[gdn-stats] <class label> head_tokens per op (token/half/amx): 0=a/b/c ...".
Header facts for the summary leaf: amx_compiled (TRON_AMX_DISPATCH defined), amx_available, amx_gdn_enabled, block_tokens (32), n_key_heads, n_value_heads, key_head_dim, value_head_dim, n_operations, n_workers, tsc_hz. In this commit amx_available comes from amx_attn_h128g4::available() under #ifdef TRON_AMX_DISPATCH (it is the process-wide AMX probe; the unit test t_amx_dispatch_dtype fakes that symbol, so do not reference any other symbol of amx_attn.cpp) and amx_gdn_enabled is false (no GDN AMX kernel exists yet; a later commit sets it).

Cost rule when the switch is off: one bool test per run_gdn_operation call, no rdtsc, no atomic, no allocation of rows.
Keep the existing TRACE_EVENT("model", "GatedDeltaNet", ...) exactly as it is (a trace analysis script selects it by name).

Verification you must do on the server (tag stats): build TARGETS="runtron t_gated_delta_net"; run ./gen/t_gated_delta_net fully (all old cases must still pass, with the same assertion counts plus yours); run your new cases also with TRON_GDN_STATS=1 in the environment; show that the generated plugin passes the stats pointer (grep the generated plugin header under gen/ for gdn_path_stats). If t_tronstats_convention or t_llama_unit exist in that tree, build and run them too. Do not run runtron.
Report the exact JSON of one rendered totals leaf and of the exit report lines (from your test) in interface_notes.`
const PARTB = `
YOUR TASK (key: partb): Part B of the design, AMX attention kernels for heads of 256 values with 4 query heads per KV head, plus task 4 of the plan (a stand-alone timing of the new kernels against the AVX-512 path).
Worktree: /home/jhan/workspace/ai-runs/tron-gdn-partb, branch jhan-gdn-partb (already created at the base commit). Build tag: partb. Benchmark CPU: 142 (one CPU only for timings; nobody else uses it).
Read first: ${U}/attnshape.report.md (all of it; it ends with the concrete change list), ${U}/attnshape.facts.md (traps), ${U}/gdntests.facts.md, design.txt section 5.5 and the task 4 and task 5 rows of section 6.

Code change (follow the change list of attnshape.report.md; where it leaves a choice, take the option with the smaller diff and say so):
- New kernels for the shape 256 x 4 in src/tron/kernels/amx_attn.cpp with declarations in h/tron/kernels/amx_attn_iface.hpp, in a second namespace amx_attn_h256g4: query packer (8 panels, 8192 bytes), QK kernel (8 dimension steps of 32 into the same 4 accumulator tiles: 32 tile products per query token, page and KV head), PV kernel (4 groups of 64 output dimensions: 32 tile products), shape gate. The three existing 128 x 4 kernel bodies stay byte for byte as they are. amx_attn_h128g4::eligible must keep returning false for (256, 4).
- available(), begin_region(), end_region() stay single functions (the existing ones) shared by both shapes.
- Dispatch in h/tron/models/self_attention.hpp: the dense-page path takes the 256 x 4 kernels when the operation has that shape. Size the packed-query slot from the shapes the model declares (a model with only 128-wide kernels keeps its 4096-byte slots), with a static_assert that the packer fits the slot. Mind the trap about value-initializing resize of the packed-query array.
- The attention statistics need no new counter; check that amx visits and K tokens are counted for the new shape.
- Tests: extend t/t_amx_numerics.cpp with the QK and PV error-band cases for 256 x 4 (same method and tolerances as the 128 cases) and a packer layout case; keep t/t_amx_dispatch_dtype.cpp linking (add fakes for the new entry points; add a 256 arm only if the existing model fixture supports it without large new code, else report it as not done); update the comments that say the kernels serve one shape. Update the Note [AMX attention dispatch].
Verification on the server (tag partb): build TARGETS="runtron t_amx_numerics t_amx_dispatch_dtype" (add t_llama_unit if that target exists in the one-model tree); run the tests; the new kernel cases must execute (no skip warning). Do not run runtron: the lead runs the A/B runs.

Task 4, stand-alone timing: write exec/gdn-impl-20261121/bench/task4_attn256.cpp and task4.sh under /home/jhan/workspace/intel-AMX/ (model them on bench/amx_gdn_bench.cpp, bench/task3.sh and exec/gdn-20261120/clock-probe.sh in the same tree; results go to /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/bench/task4-*.txt; the script takes a load snapshot first with bash /home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh). Measure on CPU 142, for one "page unit" (one query token, 4 query heads, on one 64-token page of one KV head, K 32 KiB row-major bf16 and V 32 KiB pair-interleaved bf16):
  (a) the AVX-512 path as tron runs it today for 256-wide heads (QK by bf16 dot products with VDPBF16PS as dotter<bf16,256> does it, the softmax step, PV as scaled_v does it: read h/tron/kernels/dotter.hpp and kv_cache.hpp scaled_v_expr and copy the instruction pattern, not the framework),
  (b) the new AMX kernels (copy your kernel code into the benchmark so it is stand-alone), with the same softmax step,
  each in two regimes: the pages of the test cycle fit the L1/L2 cache (for example 4 pages), and the pages come from main memory (a pool of pages far larger than the 2 MiB L2 and the L3 share, visited in an order the prefetcher cannot follow), and for prefill-like use (many query tokens visit the same page one after another) and decode-like use (one query token per page). Report microseconds per page unit, the ratio AVX-512 / AMX, and the core clock while each loop runs (sample /sys/devices/system/cpu/cpu142/cpufreq/scaling_cur_freq every 0.25 s during a 4 s loop, drop the first second, report the median; note that the AVX-512 loop must run in a process, or after a TILERELEASE, with no tile configuration loaded, because a loaded tile configuration can lower the clock of AVX-512 code too). The pass rule of task 4 is "1.5 times faster than the AVX-512 path or more, with the data in cache"; state the measured ratio against it. Run each measurement 3 times and give the range.
Report in interface_notes the names and signatures of the new entry points and the measured table of task 4.`
phase('Implement')
const res = await parallel([
  () => agent(COMMON + '\n' + STATS, { label: 'implement:stats', phase: 'Implement', schema: SCHEMA }),
  () => agent(COMMON + '\n' + PARTB, { label: 'implement:partb', phase: 'Implement', schema: SCHEMA }),
])
return { stats: res[0], partb: res[1] }
