# Procedures for the thirteen checks

Short version: one section per check in SKILL.md, with the commands an agent runs. Replace `BASE`, `HEAD`, `WT` (the worktree) and `N` (the PR number) with the review's values. Each procedure was run on PR 4557 at head 96a6220ab6 (BASE e5fa372c19) and tightened until it reproduced Wade's finding and fired on nothing he kept; the "On PR 4557" line of each section records that run with HEAD line numbers.

Common setup:

```
HEAD=$(gh pr view N --json headRefOid -q .headRefOid)   # or the reviewed head if a later push exists
BASE=$(git -C WT merge-base $HEAD origin/main)
gh pr view N --json body -q .body > body.md; cat -n body.md
git -C WT log --format='%h %an %ad %s' --date=short --no-merges $BASE..$HEAD > log.txt
git -C WT diff $BASE $HEAD > pr.diff
git -C WT diff --name-only $BASE $HEAD > prfiles.txt
for f in $(grep '^t/' prfiles.txt); do git -C WT show $HEAD:$f > full/$f; done
```

Do not fetch or change state in a worktree you were told not to change.

## Check 1: value-pinning rows need a consumer

1. List runtime assertions with a literal or table expected side in the test hunks: `git diff -U0 BASE HEAD -- 't/*' | grep -n -E '^\+.*(REQUIRE|CHECK)\(' | grep -v STATIC_REQUIRE`, plus expectation tables (`std::array<std::pair`, parallel input/expected arrays). Map each to its HEAD line through the `@@` headers.
2. Classify. A: expected equals the bits the test put in or stored or read back earlier (round trip, partner kept, at() read-back), after discounting a pure widening. Keep. A0: a value whose discarded bits are zero, so truncation and rounding agree (1.0, 0.5, a quiet NaN with zero low bits). Keep. B: a conversion or rounding policy (truncate, round, tie, flush, saturate). C: a special value changing class (NaN to inf, denormal to zero). P: a pair-invariant row (expected 0 for the untouched partner after an even write). Continue with B, C and P.
3. For each B or C row, name the accessor it stores through (set_v, append_v_row, copy_token, load_row, the function in the hunk). `git grep -n '<accessor>' HEAD -- h src` (exclude t/). Read each reader and record a reader file:line that depends on the exact bits, a documented format, an AGENTS.md line, or NONE. A comment stating the policy or its history is NONE. A rounding difference the repository already admits between its own paths is NONE. The PR body, the design document and the moved doc comment are NONE.
4. Repository rules for the value class: `grep -n -i -E 'NaN|inf|denormal' AGENTS.md t/AGENTS.md`. A rule that calls the value corruption makes a row that asserts the path converts or hides it a finding.
5. Second policy: read the test comments and the function doc comment for a "would" statement naming another conversion, or take the generic converter for the same source type (`git grep -n 'fp32s_to_bf16s\|to_bf16\|from_fp16' HEAD -- h`), and compute that converter's output for the row's input bits. A grep for the input bits alone is not enough.
6. For each P row: the test, or the function it stores through, must cite the Note naming the dependent path. If absent, the finding is "add the citation", never "drop the row".
7. Report every B or C row with NONE from step 3, every row flagged by step 4, and every row whose second policy differs (step 5). Name the rows to keep (A, A0, P).
8. Run the same steps on rows a critic or an earlier lens PROPOSES to add.

On PR 4557: tables at t/t_llama_unit.cpp:3573-3577 and :3609-3612; B rows :3574 (0x3f80ffff), :3577 (tie 0xbf818000), :3610 (65504 fp16); C row :3575 (0x7f800001 -> +inf, AGENTS.md:73-75); second policy h/tron/simd/bf16.hpp:57-69 and :89-105 (fp32s_to_bf16s keeps the NaN); kept A rows :3561-3563, :3601, :3647; P rows :3544, :3640 (Note [Zero-Initialized V Slots], cited from v_vnni.hpp:234-235).

## Check 2: structure-only compile-time checks

1. `git diff -U0 BASE HEAD -- 't/*' | grep -n -E '^(\+\+\+|@@|\+.*(STATIC_REQUIRE|static_assert))'`; map each to file:line at HEAD. For each requires-expression template used, open its definition and record which functions its body names.
2. Split by what the expression names. BOUNDARY: the body names a production function declared outside the probed type's own header. SHAPE: a type trait, sizeof, alignof, is_constructible / is_convertible / is_default_constructible, or a requires-expression whose body calls only the probed type's own members or their absence. A trait probe that spells the PR's stated type-safety contract (not constructible from a bare pointer or the other layout's view) is BOUNDARY; a positive constructibility probe on an alias goes to check 6.
3. For each SHAPE check: `git grep -n -E 'static_assert.*(is_trivially|is_default|is_constructible|is_convertible|sizeof|alignof)' HEAD -- h src | grep -i '<type or alias or enclosing type>'`. Resolve aliases. A static_assert inside a member function counts when a production caller instantiates it; cite the caller. An assert on an enclosing type that holds the probed type as a member counts.
4. For each remaining SHAPE check, open the probed type's definition. A declaration that fixes the trait (`alignas N` versus `alignof == N`, `= delete` versus a not-callable probe, an array member versus sizeof) makes the check a repeat of the declaration; report it as structure-only and drop it. MOVE applies only to a trait the type neither declares nor asserts and that a production line outside the header relies on.
5. Report: BOUNDARY kept (line range), SHAPE repeats (test line -> header file:line each), SHAPE tautologies (test line -> declaration line), SHAPE consumer-less. Check the PR body: if it advertises the assertion count or "tested with STATIC_REQUIRE", confirm the sentence refers to a BOUNDARY probe.

On PR 4557: BOUNDARY :382-390 (amx_qk_accepts / amx_pv_accepts call the kernels, templates at :95-103) and the contract probes :394-395, :399-400; SHAPE repeats :413-415 -> kv_cache.hpp:2339-2342, :422-423 -> kv_cache.hpp:1553-1556 and :1596-1599, :424 -> kv_cache.hpp:1594; tautologies :402 (as_view on a temporary, `= delete` at v_vnni.hpp:174-175), :416-418 (sizeof, array member v_vnni.hpp:178), :419 (alignof, alignas at v_vnni.hpp:156); structure-only :396 (not default constructible), :407-408 (no operator[]); :397 to check 6.

## Check 3: a layout-formula check must execute on the lane that gates the PR

1. List new or moved REQUIRE/CHECK lines whose actual side is stored bytes or indices and whose expected side is a literal table or a formula in the test or a Note. Open the full file at HEAD.
2. Walk upward to the TEST_CASE start: `grep -n 'return;\|SKIP(\|WARN(\|available()\|getenv' full/<file>`. Record every exit above the assertion and its condition. A compile-time `#if` is not a runtime exit; a `min_slices_N` label in t/CMakeLists.txt is test selection, listed separately.
3. Between the exit and the assertion, does any statement execute the probed instructions? For `available()`: a call inside begin_region()/end_region() or any function of the AMX kernel namespace. AVX-512 intrinsics do not count.
4. Lanes: for each workflow that can run the test binary, record its trigger block and whether its configure line sets the build flag the TEST_CASE needs (`git grep -n '<FLAG>' HEAD -- .github nix flake.nix CMakePresets.json CMakeLists.txt`). Flag off: the case is compiled out on that lane. Flag on: list the runners the job can land on (job `runs-on` labels) and mark those that fail the probe (README.ci.md runner table: rows without the `intel` label have no AMX).
5. Oracle: trace every function the expected side calls. If a production accessor of the same storage produces it, name the shared helper.
6. Substitutes: `git grep -n -E 'v_vnni_tensor|v_vnni_view|v_packed|append_v_row|load_row|copy_token|set_v\(|get_v\(|scaled_v\(|\.append\(' HEAD -- t/` (replace with the storage accessors of the PR) and take the enclosing TEST_CASE of each hit. Class (i) independent formula or literal table substitutes. Class (ii) route check through the same helper never substitutes. Class (iii) a second reader with its own address arithmetic substitutes only when it does not call the helper (cite its address line) and covers both parities and a pair beyond the first; then report the gap as "no assertion on the gating lane states which reader is right".
7. State the four facts: compiles on the lane; case selected; assertion reachable on the runner; log shows the path executed. The author's assertion counts can prove a skip: an AMX-on count larger than the kill-switch count by at least the comparison size, decomposed over every probe exit in the file.
8. Report the assertion line, the gate line, the lanes and runners that skip it, the shared helper, and the cheapest move.

On PR 4557: REQUIRE at t/t_amx_numerics.cpp:239 (comparison block :235-241, formula :213-217); gate :196-199 `available()` return; nothing between executes AMX (append_v_row at :233 is AVX-512); gating lane GCP Nix compiles the case out (no TRON_AMX_DISPATCH in nix/cmake-tron-test-build.nix:79-101); the deb lane's test-host job can land on andoria runners (README.ci.md:447-449, no AMX); shared helper pair_base (v_vnni.hpp:143-145) under at() and append_v_row; t_llama_unit.cpp:3701-3708 (at() section) is class (ii); the scaled_v cross-check :3387-3397 is class (iii) and covers tokens 0..6.

## Check 4: same experiment run twice

1. `git diff BASE..HEAD -- 't/*' | grep -n '^+.*\(TEST_CASE\|TEMPLATE_TEST_CASE\|SECTION(\|GENERATE(\)'` lists added or widened units. `git log --format='%h %s%n%b' BASE..HEAD -- t/` marks commits answering several gap items at once; their units are the first pair to check.
2. For each unit name the production call under test (the first production call after the unit's own writes). `git grep -n '<call>' HEAD -- t/` lists pre-existing units on the same call; one changed only in API spelling stays out.
3. Follow the call to the leaf function with branches the diff changed. Map every input (each GENERATE value, each token index) to the arm it reaches.
4. Simulate the write order of each unit: a slot counts as observed only if no later write in the same unit replaces it before an assertion reads it.
5. Record per unit the set of (branch, slot, reference, precision, read path) its assertions observe.
6. Compare pairwise. Subset: drop the smaller. Partial: name the (branch, slot) only A observes, give B that observation with one concrete edit, drop A.
7. Compare the comment above each unit with the table: "exercises N cases" holds only if the assertions observe all N.

On PR 4557: units t/t_llama_unit.cpp:3298 (poison GENERATE) and :3650/:3664 (bit-exact section), both `dst_book.append(src_book)` (:3357, :3685), both from commit 707159b9ef. copy_token arms: even<-even andnot v_vnni.hpp:359-364, even<-odd srli :378-384. Poison: dst 2 -> last copy 6<-4 (andnot), dst 3 -> 6<-3 (srli); observed slot 7 via scaled_v at :3385. Bit-exact: page of 64, last copies 63<-61 / 63<-60 overwrite every odd partner before the loop at :3687-3696 reads it; observes copied lanes against source_bits. Verdict: partial overlap; concrete edit = leave the last odd slot of the bit-exact page poisoned, require zero bits after the append, then drop the GENERATE.

## Check 5: a test name states the enforced contract

1. `git -C WT diff BASE..HEAD -U0 -- 't/*.cpp' 't/*.hpp' | grep -n '^+++\|^@@\|^[-+]'`. Drop hunks that are pure call re-spellings (no added or removed assertion, no changed comment about what the code under test does).
2. Enclosing names: `git show HEAD:<file> | awk -v L=<line> 'NR<=L && /TEST_CASE\(|SECTION\(|TEMPLATE_TEST_CASE\(|^TEST\(/ {name=$0; n=NR} END{print n": "name}'`, bounded by indentation so a closed sibling SECTION is not picked. If no TEST_CASE encloses the hunk (a helper above the first test), stop for that hunk.
3. Extract the name's verb and object.
4. Read the setup lines that put the object into its pre-call state.
5. For every assertion that observes the object, directly or through a value computed from it (follow the read path), write "fails when <state>". Skip assertions that pin a write's partner invariant; they observe the invariant, not the object.
6. The name must describe the passing state and agree with the verb of the unit's own comments. Comment flip check: `git -C WT diff BASE..HEAD -U0 -- <file> | grep -n '^@@\|^[-+] *//'`, keeping comment lines under a `@@` whose new-side start lies inside the unit.
7. Rename sites: `grep -n '<name>' full/<file>` and the PR body; commit messages only if the PR will not be squashed. List them inside the one finding.

On PR 4557: SECTION "append_v preserves poison" (t/t_llama_unit.cpp:3293); stimulus GENERATE at :3298; comment flip "must zero" at :3325; assertion REQUIRE_FALSE(std::isnan) at :3385 observes token 7 through scaled_v (:3365); rename sites: header comment :3273, commit 707159b9ef. Pre-existing units touched only by v_source_row re-spellings (:684, :1849 and eight more) do not trigger.

## Check 6: guarantee claim versus enforcing declaration

1. Extract claims: `grep -n -i -E 'compile error|cannot be (passed|handed)|reject|enforce|no (bare|raw|public) pointer|STATIC_REQUIRE|static_assert|typed view so that|neither takes' body.md pr.diff`. For each hit write (subject set, forbidden input, claimed mechanism). Expand plurals.
2. For each subject, find every parameter in the diff's added lines whose type names the subject; resolve the type through every `using` (`git show HEAD:<file>`) to its struct or class definition. Record: new class, or alias of a generic template.
3. Levels. (1) `explicit` on the pointer constructor of the resolved type. (2) Public pointer constructor present at all: `grep -n -E 'explicit|constexpr (view|const_view)\(' <definition file>`; a wrap in one expression at any call site shows the route is open: `git grep -n -E '<Alias><[^>]*>\{' HEAD -- h src t`. (3) `using` alias of a generic template: cite the alias and one other producer of the same instantiation.
4. Opposite-direction assertions: `grep -n 'is_constructible_v\|is_same_v' full/<test>` around the cited probes.
5. Design record, when present: `grep -n -i -E 'still permits|remains legal|does not prove|limitation|not a .* guarantee' <design file>`; quote any limitation the claim drops.
6. Truth table per subject with the deciding file:line for each level. The sentence holds only if every subject reads rejected at every level it implies, or the text names the open levels.
7. One finding per failing subject, anchored at the alias definition; the body row, header comment and test comment are citations, not findings.

On PR 4557: body row 65 (subjects packed V, native K); kernel parameter const_native_k_view at h/tron/kernels/amx_attn_iface.hpp:222; alias kv_cache_fwd.hpp:49-53 of const_view (view.hpp:296, `explicit`); level 1 rejected for K and V (t_llama_unit.cpp:383); level 2 open for K (:397, wrap at t_amx_numerics.cpp:165), closed for V (v_vnni.hpp:130-138 private); level 3 open for K (alias), closed for V (new class); design record round 4 row 280 "still permits an explicit ordinary pointer wrap". The limitation at t_llama_unit.cpp:392-393 clears the probes' own comment block :371-373, not the body row.

## Check 7: CI claims name the lane, the trigger and the configure line

1. Claims: `grep -n -E '\bCI\b|workflow|required check|lane|nightly|preset|build job|runner' body.md README*.md` and the diff's comment hunks. Keep sentences with a CI subject and a setting; drop measurement statements about the author's own builds.
2. Lanes: `for f in $(git ls-tree --name-only HEAD .github/workflows/); do echo $f; git show HEAD:$f | sed -n '/^on:/,/^[a-z]/p'; done`. For every file with none of push, pull_request, merge_group: `git grep -n 'uses: ./.github/workflows/' HEAD -- .github` and quote the caller's `if:` gate.
3. Setting: `git grep -n '<FLAG>' HEAD -- .github nix flake.nix CMakePresets.json CMakeLists.txt GNUmakefile README.ci.md`. Consumer per hit: a workflow `run:` line -> that job; a nix file -> the job whose `nix build` recipe imports it (follow the workflow's recipe into flake.nix); a preset -> whatever runs it. Note the CMakeLists.txt default.
4. Gating set: `gh pr checks N --json name,workflow,state,bucket`; finished only when no row is IN_PROGRESS, PENDING or QUEUED. Then `gh pr checks N --required` and record each job's workflow. For a superseded head use `gh api repos/<org>/<repo>/commits/<sha>/check-runs`.
5. Date per file: `git log --format='%h %ad %s' --date=short -S'<FLAG>' -- <file>` and `gh api repos/<org>/<repo>/commits/<sha>/pulls --jq '.[].number'`.
6. Decide: lanes disagree and the sentence names no lane (by workflow `name:`, file or job name) -> finding; the named lane's configure line contradicts the sentence -> finding; a wrong PR or date -> finding.
7. Finding with lane, trigger, configure file:line, cutover commit and the merge that brought the setting. If a reviewer cited a non-gating workflow, answer with its trigger block instead of conceding.

On PR 4557: body:17 "the configuration the required CI builds" names no lane; gating lane GCP Nix (gcp-nix.yml on: pull_request; recipe gcp-nix.yml:461-463 -> flake.nix:1229 -> nix/cmake-tron-test-build.nix:79-101, no flag; CMakeLists.txt:46 default OFF); cmake-single-platform.yml:355 ON, triggers workflow_dispatch and workflow_call only since 9a5e03687a (PR #4339), called from publish-deb.yml:68 under the tag or feature-branch gate at :64-67; flag entered it in f4889f8072 (PR #3879); the deb preset (CMakePresets.json:68, PR #4505) is a package setting, not a PR check.

## Check 8: result rows cite the reviewed head

1. Section ranges: headings whose text contains Verification, Status, Tests or Results, ending at the next heading of the same or higher level.
2. Ids: `grep -oE '\b[0-9a-f]{7,40}\b' body.md | sort -u` restricted to measurement rows in those sections. A row without an id takes the nearest "Binary:" or "at <id>" line of its section.
3. Per id: `git cat-file -t ID`; `git merge-base --is-ancestor ID $HEAD`; `gh api repos/<org>/<repo>/commits/ID` (422 = GitHub cannot show it). Not resolving or not an ancestor = twin -> finding.
4. Per ancestor id: `git rev-list --count --first-parent ID..$HEAD`; the event (a two-parent commit in ID..HEAD = merge of main); CHANGED = PR files whose content differs (`git diff --quiet ID $HEAD -- FILE`).
5. Row verdict: id == HEAD -> fine; id behind with no label -> finding; label with the unchanged PR files, the re-run date or a stated difference -> accepted. Present-tense phrase next to a non-HEAD id -> finding.
6. Ask per kind (re-run | delete when HEAD rows already stand | label).

On PR 4557: c12df586b6 ancestor, 561 commits behind incl. the merge of main e5fa372c19, 8 of 14 PR files changed; faf8ee42ca not in any ref, GitHub 422; token-identity rows cite c12df586b6 with no label; unit-test rows at 96a6220ab6 already present (body:147-156); body:133 "ran at the head c12df586b6" is present tense next to a non-HEAD id.

## Check 9: PR-body passages a GitHub reader cannot use

1. Section ranges as in check 8.
2. `grep -n -E '[0-9]{2}:[0-9]{2}(:[0-9]{2})? ?(UTC|Z)|/var/tmp/|/tmp/|/home/|[A-Za-z0-9_.-]+\.log\b|[0-9]+ [+-] [0-9]+ = [0-9]+|= [0-9]+ matches|(fewer|more) assertions than' body.md` within the ranges. No marker for `rc`; rc clauses are the keep anchor.
3. Dangling ids that label a result go to check 8. Ids in the commit table or the review-outcome table are not findings.
4. Reader test per hit; bins: clock times (keep the date), machine paths and log names (delete), reconciliations against an earlier revision (delete).
5. Report once per section, phrased as an ask.

On PR 4557: body:158 (four UTC build windows, /var/tmp log path), :160 (19:51 to 19:56 UTC), :162 (8196 = 4 + 8192 against c73e7fb2f9).

## Check 10: hunk-to-claim trace

1. Identifier set: backticked names and Note titles in "What changes" + names declared at namespace or class scope in `git diff BASE..HEAD --diff-filter=A --name-only` files, minus names with `git grep -c NAME BASE` > 0. Write the list with its `grep -c` count over pr.diff.
2. Bin commits from log.txt (SIDE / MAIN-FEATURE as in SKILL.md). Scan every non-merge commit, SIDE first: `git show <sha> -- FILE` per file.
3. Candidate hunk test: at least half of its `-` lines in `git show BASE:FILE` verbatim, at least one not blank, brace-only or comment-only, no identifier in the `+` lines. Inheritance within the same function or TEST_CASE.
4. Clearance: rename-map identity; a GitHub review thread id; a body sentence describing the added content. A sentence naming only the file or callee does not clear; a contradicting sentence is quoted.
5. Test hunks: callee untouched by the PR -> unrelated; callee rewritten -> regression guard, body gap at most.
6. Revert test (both): the hunk changes lines that exist at BASE; reverting it alone keeps every body sentence true, every identifier compiling, and every assertion passing at HEAD also passing at BASE. If the hunk is the sole test of a PR symbol's forwarded behavior, report a body gap and let the author choose.
7. One finding per hunk.

On PR 4557: ec795fbce8 (src/tron/kernels/amx_attn.cpp:152-181, 35 of 36 removed lines at BASE, 0 identifiers, body:52 "The tile loads are unchanged" contradicts) -> unrelated, split out. 39a6899446 carries t/t_heap_v2.cpp:1209-1223 (CHECK is_aligned, contract alloc_align at BASE memory.hpp:146); it is the only test of the new operator new[]'s alignment forwarding -> body gap, author's choice. 959d1ae229 partner-zero rows: callee append_v_row rewritten by the PR -> regression guard, not unrelated.

## Check 11: commit history is reviewed content

1. `git rev-list --count BASE..HEAD` and `--no-merges`; `git log --first-parent --oneline -20 origin/main` (merge commits = permanent history).
2. Per commit: `git show --stat <sha>`, `git show -w <sha>`; bin OTHER-AUTHOR / FIXUP (no behavior change AND removed non-comment lines added by an earlier PR commit, or an exact return to main's behavior) / UNRELATED (check 10) / TOPICAL.
3. Clusters: FIXUP commits naming the same Note title, or `git blame -L` of the rewritten lines at HEAD listing two or more of them.
4. Units: one per body heading that names a code change, merged with the file-set groups of the TOPICAL commits.
5. Report only a cluster or an unrelated commit; otherwise at most a one-line note.

On PR 4557: 21 commits (2 merges, 19 without) at 96a6220ab6; Wade's 20 is the with-merges count at c12df586b6; clusters a52ce4db25 / 55f0068cbf / 34b157326f (Note [DMA allocation creates objects]) and fcdbfff8e4 / 2280e4beb2 / 76502ce5b2 (packed V comments); OTHER-AUTHOR 8bbbb7c82d and 63df10cf90 (Ben); units: views and kernels and call sites; DMA allocation creates the blocks; tests.

## Check 12: a shared-header change no test observes needs a named owner's acceptance

1. Global definitions: for every touched header, map added lines to HEAD through the `@@` headers; walk `git show HEAD:F` keeping a namespace depth (+1 per `namespace X {`, -1 per `}  // namespace`); report added lines at depth 0 that are not blank, `//` or `#`. Quick pre-filter: `git diff BASE..HEAD -- '*.hpp' | grep -n -E '^\+.*(operator (new|delete)|#define|using namespace)'`.
2. Untestable claims: `git diff BASE..HEAD | grep -n -i -E 'no test (fails|can)|nothing can catch|cannot be tested|not testable|behave the same either way'` and `git log --format='%h %B' BASE..HEAD | grep -n -i -E <same>`; attribute a commit-message hit to `git show --name-only --format= <sha>` and test per file.
3. Tests on the path: `git grep -n '<function>' HEAD -- t/`; record what each asserts (by-product or mechanism).
4. Fan-out: direct = `git grep -l -E '^\s*#\s*include.*<path>' HEAD -- h src t bin ingest | wc -l`; transitive = closure over `#include` lines of every .hpp/.cpp/.h/.cc/.inl under those directories; report "N direct, M transitive of T".
5. Origin: `gh api repos/<org>/<repo>/commits/<sha>/pulls --jq '.[] | [.number,.draft,.state,.created_at] | @tsv'`; fold when another PR lists it and the commit sits on `git log --first-parent BASE..HEAD` with no merge commit of that PR. Without network: PR body and first-parent log, origin unconfirmed.
6. Owners: `git log --format='%an <%ae>' BASE -- <file> | awk '!seen[$0]++'` (recency order) + requested reviewers (`gh pr view N --json reviewRequests`) with a commit on the file; map logins with `gh api users/<login> --jq .name`, then by email local part.
7. Owner comments: `gh api repos/<org>/<repo>/pulls/N/comments --paginate | jq -r '.[] | select(.path=="<file>") | [.user.login,.created_at,.commit_id,.body] | @tsv'`; class placement accepted / diagnosis agreed / wording only; count only the first, and only when `git merge-base --is-ancestor <introducing sha> <commit_id>` succeeds. An APPROVED review by an owner at a head containing the hunk counts.
8. Emit when (placement half) AND (unobserved half) AND no accepted-placement comment.

On PR 4557: h/system/memory.hpp:197 operator new[] at depth 0 (namespace closes :165, reopens :203); :192 "No test fails if a caller goes back to calling dma_allocate_aligned directly"; tests t/t_heap_v2.cpp:1206-1239 and :1250-1278 check non-null, alignment and the empty return; fan-out 42 direct, 153 transitive of 502; origin 39a6899446 = draft #4587 folded by fast-forward; owners by recency Ben Gamari, Alexey Radul (axch), Brian Hamon; Ben's comments 4133772400 ("Can you clarify?") and 4133869073 (diagnosis agreed, reword requested) at commit_id c73e7fb2f9; no placement acceptance; jhan's reply cites 39a6899 (2026-09-23) for a thread of 2026-09-29.

## Check 13: role-bearing constant names

1. `git diff BASE HEAD | grep -nE '^\+.*\b[A-Z][A-Z0-9_]*_(0X[0-9A-F]+|[0-9]+|TRUE|FALSE) *= *[^=]'` (definitions only; `[^=]` excludes `==`). Record file:line at HEAD.
2. Strip the suffix; group by stem within one file. A family = two or more names with one stem. Stems that differ by a word are not a family.
3. Family: `git show HEAD:<file> | grep -n 'STEM_'`; per member write what data it holds at each use site, quoting the line. Flag unless scratch rotation (same data at every site, comment says so).
4. Single name: the stem must say what the value is or selects. Guide exceptions: literal 0 for init, reset, comparison or empty value when the parameter name is visible at the call or the statement is an init, reset or comparison; a numeric literal inside a one-use `alignas`.
5. Duplicate (production constants only): `git grep -n -E '= <value>;' HEAD -- h src`; report when an existing constant states the same meaning, has the same value in every build and is reachable through the file's includes. Never for a constant defined in a test.
6. Report file:line, the stem, what the use sites show, the sibling naming form in the same file. Never the suffix.

On PR 4557: 35 definitions; one family ACCUMULATOR_TILE_0..3 (src/tron/kernels/amx_attn.cpp:43-46): in qk_rowmajor_128x4 tile i holds K block i scores (:175-178), in weights_times_v_128x4 output dims 16i..16i+15 (:268-271); sibling form per kernel K_EVEN_BLOCK_TILE_4 (:49) and P_TILE_4; single names BF16_BITS_16, V_ODD_TOKEN_LANE_MASK_0XFFFF0000, APPENDED_TOKENS_7, PATTERN_BASE_0X3C00 carry a role and are not findings; V_PLANE_ALIGNMENT_64, ARENA_ALIGNMENT_64 and HEAD_SIZE_64 are not duplicates (unreachable or test-local).
