## Check 14: added symbol, include, parameter, branch or header needs a consumer

Setup: `BASE=$(git -C WT merge-base HEAD origin/$(gh api repos/positron-ai/tron/pulls/N --jq .base.ref))`; on a merged PR (returns HEAD) use `--jq .base.sha`.

1. Constants: `git -C WT diff -U0 BASE HEAD -- h src t | grep -oE '^\+\s*(inline\s+)?(static\s+)?constexpr\s+[A-Za-z_0-9:]+\s+[A-Za-z_][A-Za-z_0-9]*' | awk '{print $NF}' | sort -u`
2. Functions: `git -C WT diff -U0 BASE HEAD -- h src | grep -E '^\+(inline |static )?[A-Za-z_:<>]+ [A-Za-z_][A-Za-z_0-9]*\(' | grep -vE ';\s*$' | grep -oE '[A-Za-z_][A-Za-z_0-9]*\(' | tr -d '(' | sort -u`; drop names `git -C WT grep -w "$n" BASE -- h src t bin` finds; aliases: `grep -E '^\+\s*(using [A-Za-z_]+ =|extern )'` on the diff over h src t.
3. Consumers: `git -C WT grep -n -w "$n" HEAD -- h src t bin ingest | grep -v -E "constexpr [A-Za-z_0-9:]+ $n *=" | wc -l` (`-w`, never `NAME\s*\(`).
4. Promise: `git -C WT show HEAD:FILE | sed -n "$((L-10)),${L}p" | grep -n -i -E 'called (between|after|before|on|when)|reset|clear|release'`
5. Definition: `git -C WT grep -n -E "^[A-Za-z].* $n\(" HEAD -- src h`
6. Includes: `git -C WT diff -U0 BASE HEAD | grep -E '^\+\+\+ |^\+#include'`; per X in F: `git -C WT show HEAD:F | grep -n -w -E 'NAME1|NAME2' | grep -v '#include'`, same on `BASE:F`; `git -C WT log --format='%h %s' --no-merges BASE..HEAD -- F`; `git -C WT show HEAD:F | grep '^#include' | sort | uniq -d`
7. Parameters: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^@@ -[0-9]+,0 \+[0-9]+ @@ .*[A-Za-z_]+\(' -A1`; then `git -C WT grep -n 'FUNC(' HEAD -- h src t`
8. Branches: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^\+\s*if \('`; `git -C WT diff -U3 BASE HEAD | grep -n -A3 -E 'ASSERT\(false|std::unreachable|abort\('`; `grep -n 'TRACE_EVENT_END("SPAN")'` on `HEAD:FILE`
9. Headers: `for f in $(git -C WT diff --name-only BASE HEAD -- 'h/*.hpp'); do git -C WT grep -l -E "#include .*$(basename $f)" HEAD -- h src t bin ingest | grep -v "^HEAD:$f$" | wc -l; done`
10. Lift: `gh pr view N --json title,body | grep -i -E 'step [0-9]|phase [0-9]|lifts?\b|pulls? in'`

On PR 2903 (HEAD 64ea13a671, BASE 947d045a14): short_timeout_ns consumers=0 (h/pos/config.hpp:49), gone at b8739108f7. PR 1920 (2d53016b44, b604cb860a): dump_kv_cache_from_hbm h/pos/hwattention.hpp:1145, dump_qkv_data :1177 callers=0; t/t_hwattention.cpp:2, :13, :27 zero uses (dd2ced785b). PR 2287 (c459e255d9): clear_kv_complete kv_cache.hpp:560 callers=0, promise :559.


## Check 14: spelling, wrong names and over-wide lines in added prose

BASE: open PR `BASE=$(git -C WT merge-base HEAD origin/$(gh api repos/positron-ai/tron/pulls/N --jq .base.ref))`; merged PR `BASE=$(gh api repos/positron-ai/tron/pulls/N --jq .base.sha)`. Scripts: references/check14/.

1. `git -C WT diff BASE HEAD > pr.diff; python3 -I prose.py WT HEAD pr.diff > prose.txt`
2. `{ git -C WT grep -ohE '[A-Za-z_][A-Za-z0-9_]{2,}' BASE -- h src t; for f in $(grep '^+++ b/' pr.diff | sed 's#^+++ b/##' | grep -E '^(h|src|t)/.*\.(hpp|cpp|h|c|inl)$'); do git -C WT show HEAD:$f | sed -E 's#//.*$##; s#"([^"\\]|\\.)*"##g' | grep -v -E '^\s*(\*|/\*)' | grep -oE '[A-Za-z_][A-Za-z0-9_]{2,}'; done; git -C WT ls-tree -r --name-only HEAD | sed 's#.*/##; s#\..*$##'; } | tr 'A-Z' 'a-z' | tr '_' '\n' | grep -E '^[a-z]{3,}$' | sort -u > lexicon.txt`
3. `uv run -q --with pyspellchecker python -I spell.py prose.txt lexicon.txt > spell.txt; grep -E '^(BAD|VOCAB)' spell.txt` (fallback `uvx codespell prose.txt`)
4. `for w in $(grep EXCUSED spell.txt | grep -v '(affix)\|(prefix)' | awk '{print $2}'); do s=${w%s}; c=$(git -C WT grep -n -i -E "$s" HEAD -- h src t | sed -E 's#//.*$##; s#"([^"\\]|\\.)*"##g' | grep -v -E '^[^:]+:[0-9]+:\s*(\*|/\*)' | grep -i -c -E "$s"); [ "$c" -eq 0 ] && echo "read: $w"; done`
5. `uv run -q --with pyspellchecker python -I step5.py WT HEAD prose.txt | grep '^FIND'`
6. `for f in $(git -C WT diff --name-only BASE HEAD -- '*.md'); do echo "== $f"; git -C WT show HEAD:$f | awk '/^```/{f=!f} !f && /^#/{print NR": "$0}'; done`
7. `python3 -I width.py WT HEAD pr.diff`; only on a hit: `git -C WT show HEAD:GNUmakefile | sed -n '/^format:/,/^$/p'; git -C WT grep -n -i -E 'markdown|mdformat|prettier|codespell|markdownlint' HEAD -- GNUmakefile lefthook.yml .github nix flake.nix`
8. Read each added comment sentence once for a repeated or dropped word (2915260657). One suggestion block per line; never above nit.

On PR 2233 (HEAD af9438799a, BASE de8081fac4): step 3 BAD doc/shard_based_hw_attention_api.md:28 ombined, :51 lanch, :53 implementaion, h/libpos.hpp:238 soem, :239 slidign, src/pos/worker.cpp:803 thsi, :811 thie; step 6 doc :37 lowercase against :25; Wade posted doc :28, :51, :55, worker.cpp :791, :803. On PR 2499 (BASE 9ef4586a57, HEAD 214156bd44): step 5 FIND LOG_TOKEN_TIMS h/runtron/stream_generate.hpp:36, neighbour LOG_TOKEN_TIMES (3125494616). On PR 3386 (BASE 989c979c25, HEAD 70d4cfc4a1): step 7 capture.md:193 width 144 vs 94, README.perfetto.md:273 width 130 vs 79 (3778051701, 3778058064).


## Check 13: a number in production code carries its role

0. `BASE=$(git -C WT merge-base HEAD origin/$(gh api repos/positron-ai/tron/pulls/N -q .base.ref))`; merged: `BASE=$(git -C WT merge-base HEAD $(gh api repos/positron-ai/tron/pulls/N -q .merge_commit_sha)^1)`.
1. `git -C WT diff -U0 BASE HEAD -- h src | grep -E '^\+[^+]' | sed -E 's#/\*.*\*/##g; s#//.*$##; s#"([^"\\]|\\.)*"#""#g' | grep -nE '(^|[^A-Za-z0-9_.])([2-9]|[1-9][0-9]+)([^A-Za-z0-9_.]|$)|0[xX][0-9a-fA-F]+'`; drop hits the paired `-` line (`grep -B1 -F`) already carried.
2. FILE L: `git -C WT show HEAD:FILE | awk -v L=L 'NR<=L && /^[[:space:]]*[A-Za-z_][^;=]*\)[[:space:]]*(const|noexcept|override)?[[:space:]]*\{[[:space:]]*$/ && !/^[[:space:]]*(if|for|while|switch)\b/ {s=NR; ind=match($0,/[^ ]/)-1} NR>L && s && !e && match($0,/[^ ]/)-1==ind && /^[[:space:]]*\}/ {e=NR} END{print s, e}'`; scan `sed -n 's,ep'` as in step 1; keep only when `git -C WT diff BASE HEAD -- FILE | grep -nE '^[-+ ].*\bNAME\b'` lists the step-3 name.
3. `git -C WT grep -n -E '(constexpr[^=;]*=[[:space:]]*|#define[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+)\bLIT\b' HEAD -- FILE h/pos/config.hpp`.
4. `git -C WT diff -U0 BASE HEAD -- h src | grep -E '^-[^-]' | grep -oE '\b(tron|hardware|pos)::[a-z_][a-z0-9_:]*\b|\b[A-Z][A-Z0-9_]{3,}\b' | sort -u`; `git -C WT diff -U0 BASE HEAD -- h src | awk -v S=STEM -v V=VALUE '/^-/ && index($0,S) {r[++n]=$0; next} /^\+/ && n {for(i=1;i<=n;i++) if ($0 ~ /sizeof\(/ || $0 ~ ("[^A-Za-z0-9_.]" V "[^A-Za-z0-9_.]")) {print r[i]; print $0; break}} !/^[-+]/ {n=0}'`; `git -C WT log --oneline -m -S'STEM' BASE..HEAD -- FILE`.
5. `git -C WT diff -U0 BASE HEAD -- h | grep -E '^[-+].*(constexpr|#define)[^=]*=[[:space:]]*[0-9]'`; `git -C WT grep -n -E '"[^"]*\bOLD\b[^"]*"' HEAD -- $(git -C WT grep -l 'NAME' HEAD -- src h)`.
6. `git -C WT diff BASE HEAD -- h src | grep -nE '^\+.*(reserve|resize|assign)\(([2-9]|[1-9][0-9]+)|^\+.*constexpr[^=]*=[[:space:]]*[0-9]+;|^\+.*(alloc|size|offset|addr|stride)[^;]*[*/][[:space:]]*[A-Za-z_][A-Za-z0-9_]*(_B|_size|_pages|_per_|_depth|_ring)'`.
7. `git -C WT diff BASE HEAD -- h src | grep -nE '^\+.*return (NUM_|MAX_|[A-Za-z_]*(_count|_COUNT|SIZE|size\(\)))'`.
8. `git -C WT diff BASE HEAD | grep -nE '^\+.*\b[A-Z][A-Z0-9_]*_(0X[0-9A-F]+|[0-9]+|TRUE|FALSE) *= *[^=]'`.

On PR 2176 (BASE 1794cdf67d, reviewed 9553cd0a11): step 2 keeps h/pos/hwattention.hpp:772 `(tok_idx / 128)` (2948416014); step 4 pairs POS_DATA_SIZE (h/pos/regs.hpp:40) with `sizeof(bf16)` at src/pos/hwattention.cpp:51 (2948209837); step 6 lists src/pos/gof.cpp:98 (2947992404).


## Check 16: debug switch, dump, include, print or trace promotion that ships on

1. `BASE=$(git -C WT merge-base HEAD $(gh api repos/positron-ai/tron/pulls/N --jq .base.sha))`.
2. Flips: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^(\+\+\+|@@)|^[-+] ?(// ?)?#define [A-Z_0-9]*(DEBUG|DUMP|TRACE|VERBOSE|LOG|HEXDUMP|TIMERS)[A-Z_0-9]*'` and `... | grep -n -E '^-// ?#define [A-Z_0-9]+'`; keep `+#define NAME` with a `-// #define NAME` twin or no twin; drop `+//` lines and value-edit pairs.
3. What ships: `git -C WT show HEAD:FILE | grep -n -E '#ifdef NAME|#if .*NAME|defined\(NAME\)'`; ladder: `git -C WT show HEAD:FILE | grep -n -E '^(// ?)?#define [A-Z_0-9]+( [0-9]+)?$'`.
4. Dumps: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^\+.*(debug_hexdump\(|debug_bf16dump\(|[^a-z_]dump_[a-z_]*\(|spdlog::debug\()' | grep -v -E '^[0-9]+:\+ *(//|inline |void |static )'`; guard walk: `git -C WT show HEAD:FILE | awk '/^#if/{d++; g[d]=$0} /^#el(se|if)/{g[d]=g[d]" [else]"} /^#endif/{d--} /PATTERN/ && $0 !~ /^ *\/\// && $0 !~ /^#define/ {printf "%d: depth=%d", NR, d; for(i=1;i<=d;i++) printf " <%s>", g[i]; print ""}'`, PATTERN = `debug_hexdump\(|debug_bf16dump\(|spdlog::debug\(`. GUARDED = `#ifdef NAME` on the stack, NAME on the ladder or DEBUG-stem. spdlog::debug fires only within 3 lines of a `dbg_<x>_log` call.
5. Wrong switch: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^\+#define dbg_[a-z_]*log'`; then `git -C WT diff -U0 BASE HEAD -- FILE | grep -n -A1 -E '^\+.*dbg_[a-z_]*log\($'`; classify each call by its message subject.
6. Include: `git -C WT show HEAD:INCLUDED | grep -oE '^(inline|static|constexpr|struct|class|using|void|bool|int|auto)[A-Za-z_0-9<>:, *&]* ([A-Za-z_][A-Za-z_0-9]*) *(\(|\{|=|;)' | sed -E 's/ *(\(|\{|=|;)$//' | awk '{print $NF}' | sort -u`; walk each name with step 4, no namespace.
7. Trace: `git -C WT diff -U0 BASE HEAD -- h src | grep -n -B1 -A1 -E '^[-+].*TRACE_EVENT\('`; `git -C WT show HEAD:perfetto/apponly.cfg | grep -n -E 'size_kb|fill_policy|enabled_categories|disabled_categories'`.
8. Leftovers: initials from `gh pr view N --json author -q .author.name`; `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^\+.*spdlog::(debug|info|warn)\("INITIALS '`; gating literal `... | grep -n -E '^\+.*\? *[a-z_]+ *: *""'`.

On PR 1973 (BASE ec16f160f5, HEAD 5e0606f0d8): step 2 lists h/tron/models/self_attention.hpp:20 DEBUG_GET_ALLKV, :25 MORE_HWATTN_DEBUG, src/pos/worker.cpp:80 DEBUG_HWATTN_CMD_GEN; step 3: self_attention.hpp:21 include, :500 dump, worker.cpp:117, ladder :73-:86 = 2759894229, 2759903853; base hwattention_sync.


## Check 17: comment, log label or doc clause matches the line it describes

BASE: `BASE=$(git -C WT merge-base HEAD origin/$(gh api repos/positron-ai/tron/pulls/N --jq .base.ref))`. Merged PR: P = first parent of `git -C WT log --first-parent --format='%h %p %s' origin/main | grep -m1 '#N'`; BASE = merge-base HEAD P.

1. `git -C WT diff -U0 BASE HEAD -- h src > pr0.diff; grep -n -E '^\+\+\+|^@@|^\+\s*(//|/\*|\*)|^\+.*(spdlog::|_log\(|fmt::format\(|TRACE_EVENT\()' pr0.diff > step1.txt`; `git -C WT diff -U0 BASE HEAD -- '*.md' | grep -n -E '^\+\+\+|^@@|^\+[^+]' > step1-md.txt`. Map `+` lines to HEAD via `@@`; drop `+` lines equal to a `-` line. Tokens, `+` lines only: `grep -oE '\b[a-z][a-z0-9]*(_[a-z0-9]+)+\b|`[^`]+`|<[a-z_]+>|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+\.[a-z]+\b|Q\.?[0-9]+(\.[0-9]+)?|\((no|without) [a-z_ ]+\)'`.
2. `grep -E '^\+\s*(//|\*).*\b(captured from|comes from|set by|is set|sets|reads|waits? (on|for)|already set|uses|performs|divides)\b' step1-new.txt | grep -E '\b[a-z][a-z0-9]*_[a-z0-9_]+\b|`[^`]+`'`. Per token: `git -C WT grep -q -w TOKEN HEAD -- h src || echo NOSYM`. Described statement: `git -C WT show HEAD:FILE | sed -n 'L,L+90p' | grep -n -E '\bSUBJECT\b *=|\bSUBJECT\.(load|store|wait)|\bSUBJECT\('`, first hit. Siblings: `... | grep -oE '\b[a-z]+STEM\b' | sort | uniq -c`.
3. `grep -n -A3 -E '_log\("|spdlog::|fmt::format\("' full/FILE`; alias: `sed -n 'L-15,Lp' full/FILE | grep -n 'ARG *='`.
4. `grep -n -E '^\+.*(//|\*).*<[a-z_]+>' pr0.diff`; `git -C WT grep -n -F 'PREFIX' HEAD -- src`.
5. `git -C WT cat-file -e HEAD:PATH 2>/dev/null || git -C WT cat-file -e HEAD:h/PATH 2>/dev/null || git -C WT grep -q -F "\"PATH\"" HEAD -- h src t || grep -q -E "(^|/)PATH$" prfiles.txt || echo "MISSING PATH"`.
6. Tense: `git -C WT diff BASE HEAD -- FILE | grep -n -E '^-.*(recurs|F\()'`; `git -C WT show HEAD:FILE | awk '/F\(/{p=1} p' | grep -c -E 'recurs|F\('`.
7. `grep -n -E '^\+\s*(//|\*).*\?\s*$' step1.txt step1-md.txt`; `git -C WT diff BASE HEAD | grep -n -E '^-.*(Proposed change|originally)'`.
8. Negation: `git -C WT show HEAD:FILE | awk '/F\(/{p=1} p' | grep -c -i X`.
9. Option owner: `gh pr view N --json body -q .body | grep -n -iE 'new \*{0,2}[a-z]+\*{0,2} option'`; `git -C WT grep -n -F -- '--OPTION' HEAD -- src bin`.

On PR 3008 (HEAD 17c6e0117d, BASE dd5dd82caf): 133 added, 63 moved, 70 new lines; c68ea87f48:src/pos/worker.cpp:1112 names ares_fields, statement :1138 `hbm_cnt = wres_fields.fields.hbm_cnt;` (3437533506); 18 log lines, 0 findings. PR 2980: h/pos/device.hpp:663 `<bdf>` versus src/pos/device.cpp:625 dev->idx (3405930260).


## Check 18: new code re-derives what an existing helper already provides

BASE, from the PR's base branch: `BASE_REF=$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName); BASE=$(git -C WT merge-base HEAD origin/$BASE_REF)`.
1. Candidates:
```
git -C WT diff -U0 BASE HEAD -- h src > prod.diff
grep -n -E '^\+.*(std::)?getenv\("[A-Z0-9_]+"' prod.diff
grep -n -E '^\+.*while \(\*?[A-Za-z_>.-]+ *!= *[A-Za-z_]+\)' prod.diff; grep -n -E '^\+.*(rdtsc\(\)|ns_to_cycles|timeout_cycles)' prod.diff
grep -n -E '^\+[^/]*(configure|_init|setup)[A-Za-z_]*\([^)]*\b[0-9]+(\.[0-9]+f?)?\b' prod.diff | grep -v -E '^[0-9]+:\+ *//'
grep -n -E '^\+.*((1(\.0f?)?|1\.f) */ *(std::)?sqrtf?\(|rsqrt\(|/ *(std::)?sqrtf?\([^)]*head_size)' prod.diff
grep -n -E '^\+ *return [A-Za-z_.()]+ *[-+*/] *[A-Za-z_.()]+( *[-+*/] *[A-Za-z_.()]+)?;' prod.diff
grep -n -E '^\+ *\} else \{' prod.diff
grep -n -E '^\+.*\.(commit|push|push_back)\(' prod.diff
grep -n -E '^\+.*(while|for) \(.*\.size\(\)' prod.diff; grep -n -E '^\+.*\.resize\(' prod.diff
```
Drop: same call on the paired `-` line; non-model literal; one-statement else; commit sequence without ordered twin; post-loop call not re-walking; resize without grow loop.
2. Owner, callers (STEM: strip TRON_/POS_/RZ_, USE_/ENABLE_/DISABLE_/NO_):
```
git -C WT grep -n '<operand>' HEAD -- h src; git -C WT grep -n '<operand>' BASE -- h src; git -C WT grep -n '<helper>' HEAD -- h src
git -C WT grep -n -E 'getenv\("[A-Z0-9_]*<STEM>[A-Z0-9_]*"' HEAD -- h src; git -C WT grep -n -i -E '<stem>_(enabled|disabled|on|off)\(' HEAD -- h src
```
3. No owner at BASE: `git -C WT log --format='%h %ad %an %s' --date=short --until=<review date> -S'<operand>' BASE..origin/$BASE_REF --not HEAD -- h src`
4. `git -C WT show HEAD:<helper file> | sed -n '<a>,<b>p'`; twins: `diff <(git -C WT show HEAD:F | sed -n 'A1,A2p') <(git -C WT show HEAD:F | sed -n 'B1,B2p')`.
5. Copies:
```
git -C WT grep -n -E 'reservation\.commit\(\)|guard\.commit\(\)|tracker(->|\.)push\(' HEAD -- h src; git -C WT grep -n 'Descriptors are live\|disarm rollback' HEAD -- h src
git -C WT log --format='%h %ad %s' --date=short -S'<call>' -- <file>; gh api repos/positron-ai/tron/commits/<sha>/pulls --jq '.[].number'
```
6. `git -C WT show HEAD:README.code-org.md | sed -n '/Dependencies (aspirational)/,/^$/p'`

On PR 4596 (HEAD 0f784c44ff, BASE 66c7bb8db1): `pool_worker` h/tron/models/attn_stats.hpp:431-435 vs h/tron/models/self_attention.hpp:797; callers :1343, :1485 = 4147010638. On PR 2287 (HEAD 4274d5878a, BASE ba1bed266d): model.hpp:820 vs hw_attn_config.hpp:17 = 3029194687.


## Check 19: Declaration types and initializers (counts, struct locals, literal globals, sweeps)

0. `P=repos/positron-ai/tron/pulls/N`; BASE `git -C WT merge-base HEAD origin/$(gh api $P -q .base.ref)`; merged: `git -C WT merge-base HEAD $(gh api $P -q .merge_commit_sha)^1`.
1. `git -C WT diff -U0 BASE HEAD -- src h | grep -E '^\+[^+].*\b(int|int32_t|int64_t|long)[ &]+([a-z_]*(count|cnt|blocks|bytes|size|total|idx|index)[a-z_]*|[a-z_]*_per(_[a-z_]*)?|num_[a-z_]*|len|[a-z_]*_len|len_[a-z_]*|[a-z_]*_len_[a-z_]*)\b'`
2. `git -C WT show HEAD:FILE | grep -n -E '\b(int|int32_t|int64_t|long|uint32_t|uint64_t|size_t)[& ]+NAME\b'`; `grep -n -E '\(uint64_t\)\(NAME\b'`; `grep -n -E '\.[a-z_]+ = NAME;'` then `git -C WT grep -n -E '\b(uint32_t|uint64_t|size_t) F;' HEAD -- h`; `grep -n -E 'NAME *(<|<=) *0|NAME *= *-1'`.
3. `git -C WT diff -U0 BASE HEAD -- src h | grep -E '^\+\s+(struct )?[A-Za-z_][A-Za-z0-9_:<>]*\s+[a-z_][a-z0-9_]*;\s*(//.*)?$' | grep -v -E '^\+\s*(return|co_return|throw|delete|goto|break|continue|using|typedef)\b' | grep -v -E '^\+\s+(std::|boost::)' | grep -v -E '\b(int|uint[0-9]+_t|int[0-9]+_t|size_t|bool|float|double)\s'`; `git -C WT grep -l -E 'struct T\b|class T\b' HEAD -- h src`; `git -C WT show HEAD:HEADER | sed -n '/struct T {/,/^};/p' | grep -n -E '^\s+[A-Za-z_].*;'`.
4. `git -C WT diff -U0 BASE HEAD -- src h | grep -E '^\+[A-Za-z0-9_:<>]+\s+[A-Z][A-Z0-9_]+\s*=' | grep -v -E 'const|constexpr|\w+\([^)]*\);$'`; `git -C WT grep -n -E '\bNAME\b' HEAD -- src h | grep -v -E '^[^:]+:[0-9]+:\s*[A-Za-z0-9_:<>]+\s+NAME\s*=' | grep -E 'NAME\s*(=[^=]|\+\+|--|\+=|-=)|&NAME\b'`.
5. `gh pr view N --repo positron-ai/tron --json body -q .body | grep -n -i -E '(add|default|explicit|consisten|safe)[^.]{0,80}initializ|initializ[^.]{0,80}(add|default|explicit|consisten|safe)'`; `git -C WT grep -n -E 'new T\b' HEAD -- src h`; `git -C WT show HEAD:HEADER | sed -n '/^  T(/,/{/p'`.
6. `git -C WT ls-tree --name-only HEAD AGENTS.md t/AGENTS.md .github/AGENTS.md ingest/AGENTS.md`; `git -C WT grep -n -i -E 'initializ|unsigned' HEAD -- <listed>`; `grep -n -i -E 'unsigned|initializ' ~/.claude/skills/cpp-coding-guide/SKILL.md`.

On PR 3008 (BASE dd5dd82caf, REV 40e4cea98609): step 1 src/pos/worker.cpp:1693-1696 (`int expected_blocks` to `int64_t pad_bytes`); step 2 :1492 -> h/pos/device.hpp:139 `uint64_t results_per_block;`, casts :1519/:1524/:1532/:1555 (3430026641). PR 2011 (BASE ab75e61d83, REV e091f3f799): step 3 h/pos/hwattention.hpp:502/:578/:627/:657, h/pos/device.hpp:187-196 0/5 init (2789725609). PR 1485 (08b5f10085): step 4 src/pos/mwaitx.cpp:16 (2380221355).


## Check 20: an identifier states its role

1. `base_ref=$(gh api repos/positron-ai/tron/pulls/N --jq .base.ref)`; `BASE=$(git -C WT merge-base HEAD origin/$base_ref)`. If it prints HEAD (merged PR): `git -C WT log --merges --format='%H %P %s' origin/$base_ref | grep <PR head>`, then `BASE=$(git -C WT merge-base HEAD <first parent>)`. Never `<commit>~1`.
2. `git -C WT diff -U0 BASE HEAD -- h src .github/workflows | awk '/^\+\+\+ /{f=substr($2,3); next} /^@@/{split($3,a,/[,+]/); n=a[2]-1; next} /^\+/{n++; print f":"n": "$0}' > added.txt`
3. Bins: `grep -E '\w+\s*(\{\}|= [^;]*)?;\s*//' added.txt` (comment); `grep -E '\+\s*(bool|int|size_t|uint32_t|uint64_t)\s+\w+\s*(=|\{|;)' added.txt` (flags); `grep -E '\w+\s*\(.*\)\s*(noexcept|\{|const|;)' added.txt | grep -E '\b(const\s+)?[A-Za-z_:<>]+[*&]?\s+[a-z]{1,3}\s*[,)]'` (short params); `grep -E '\b\w*(indefinitely|forever|never|always|once|all|every|traced|untraced|prepare|launch)\w*\s*\(' added.txt`; `grep -E '_(untraced|impl|inner)\s*\(' added.txt`; `grep -E 'labels\.\*\.name|label\.name' added.txt`
4. Removed names: `diff <(echo '<old ids>' | tr '_' '\n') <(echo '<new id>' | tr '_' '\n')`
5. Siblings: `git -C WT show HEAD:FILE | awk 'NR>=A && NR<=B'`, then `grep -nE '\b<stem>\w*\b'` and `grep -nE 'if \(<stem>\w*\)'`; members: `grep -n '<struct>(' <header>`; `git -C WT grep -n '<struct>::<struct>(' HEAD -- src`
6. Spelling: `git -C WT show HEAD:FILE | sed -n 'A,Bp'`; `git -C WT grep -n '<fn>(' HEAD -- h src`; `for w in <short...> <long...>; do printf '%s ' $w; git -C WT grep -w -c "$w" BASE -- h src | awk -F: '{s+=$NF} END{print s+0}'; done`
7. Behavior: `git -C WT show HEAD:FILE | sed -n 'A,Bp'`; `grep -nE 'timeout|options|break|return|while|for \(|SUPPORTED'`; `git -C WT grep -n '<callee>(' HEAD -- h src`; `grep -n -i -E 'scheduler|follow-up|later PR|moved' body.md`
8. Wrapper split: `git -C WT show BASE:<file> | grep -n '<public name>\s*('`; `git -C WT show HEAD:<header> | grep -n -B3 '<name>_untraced'`; `git -C WT grep -n '<name>(' HEAD -- h src t`
9. Labels: `git -C WT grep -n -E 'labels\.\*\.name|label\.name' BASE -- .github/workflows`; `gh label list --repo positron-ai/tron --limit 200 | grep -i <word>`; `grep -n '<new string>' <new workflow file>`

On PR 2089 (HEAD 57af5033da, BASE 97f0f99674): step 3 lists src/tron/gof.cpp:55 `gof_configure(size_t nk, size_t nh, size_t hs, float scalar)`; call site h/tron/models/model.hpp:761 passes `n_kv_heads, n_heads, head_size`; BASE counts 202/92/383 versus nk 0, nh 0, hs 4 (heap_start, counted zero); Wade's suggestion 2897235803 applied in de3bb7c7 gof.cpp:55.


## Check 14: explanation at the declaration

1. Parameters: `grep -n -E '^\+[[:space:]]+[A-Za-z_:<>*&]+ [A-Za-z_0-9]+ = [^,;()]+(,|\)[^;{]*\{)$' pr.diff`. Leading comment: `git -C WT show HEAD:FILE | head -n $((LINE-1)) | tac | awk '/^[[:space:]]*(\/\/|\*|\/\*)/ {print; next} NF {exit}' | tac | grep -c NAME` (0 = candidate). Hedge words: hint|tmp|temp|opt|maybe|hack. Callers: `git -C WT grep -n -A6 'FUNCTION(' HEAD -- h src t`; drop if no hedge word and a caller omits it.
2. Env vars: `grep -n -E '^\+.*getenv\("([A-Z0-9_]+)"' pr.diff`; drop VAR read on a `-` line or by `git -C WT grep -c 'getenv("VAR")' BASE -- h src t bin` elsewhere; then `git -C WT grep -n -w VAR HEAD -- README*.md doc h src t bin | grep -v 'getenv("VAR")'` (0 = candidate).
3. Routines, per f in prfiles.txt: `git -C WT show HEAD:$f | awk -v F=$f '/^(static |inline |template)?[A-Za-z_:<>*&, ]+ [A-Za-z_0-9:]+\(.*\)[^;]*\{$/ && $0 !~ /^[[:space:]]*:/ && prev !~ /^[[:space:]]*(\/\/|\*|\*\/|\/\*)/ {print F":"NR": "$0} {if ($0 !~ /^[[:space:]]*$/ && $0 !~ /^[[:space:]]*(TRON\(|template[[:space:]]*<|\[\[|#)/) prev=$0}'`; keep `+` definitions absent at BASE (`git -C WT show BASE:FILE | grep -c 'NAME('` = 0). Length: `awk -v L=LINE 'NR>=L {n++; d+=gsub(/\{/,"{"); d-=gsub(/\}/,"}"); if (d>0) seen=1; if (seen && d==0) {print n; exit}}'` (keep >= 20). One nit per PR.
4. Test-only helpers: `awk '/^diff --git/{f=$3} /^@@/ && f ~ /^a\/h\// {print f": "$0}' pr.diff | sed 's/@@.*@@//' | sort -u`; per NAME `git -C WT grep -n -E "\bNAME\(" HEAD -- h src t bin ingest | grep -v -E "HEADER:(DEFLINE|DOCLINE)"` (all t/ = test-only). Doc block: `sed -n 'DOCSTART,DEFLINEp' | grep -E '\b(UT|[Tt]est|[Tt]est-only|[Pp]roduction)\b'`. Forwarded call: `sed -n 'DEFLINE,/^}/p' | grep -n -E 'return [A-Za-z_]+\('`, then `git -C WT grep -n -A3 'CALLEE(' HEAD -- h src`; fire only when every production call passes one named constant there.
5. Specs only: `grep -E "^\+.*(^|[ (])'[A-Za-z][A-Za-z -]+'([ ,.)]|$)" pr.diff` (first occurrence in the hunk, no `^#.*gloss` row, no link = candidate); `grep -n -i -E '^\+.*(superseded|deprecated|legacy)' pr.diff` (no `retire|delete|remove` in the status section = candidate).
6. One question per candidate at the declaration; remedy = comment, @param line, glossary row or link. Never a Note.

On PR 4007 at 29a39ac33e (BASE 21162f5568): xfer_k_entry h/pos/hwattention_dump.hpp:1023, caller t/t_hwattention.cpp:418 only, doc block :1003-1022 silent, callee xfer_k_packed_entry (:977) gets HW_BAKED_HEAD_SIZE from src/pos/hwattention.cpp:26, test passes head_size (:419) = fired (3866590750).


## Check 22: redundant statement, member, branch, specifier or scope (nit)

1. `gh pr view N --repo positron-ai/tron --json baseRefName,baseRefOid`; `BASE=$(git -C WT merge-base HEAD <baseRefOid>)` (not origin/main: a merged PR's live branch returns HEAD). `git -C WT diff -U0 BASE HEAD > pr-u0.diff; git -C WT diff BASE HEAD > pr.diff`.
2. Shape a: `grep -nE -A1 '\.(push_back|emplace_back)\(' pr-u0.diff | grep -E '^[0-9]+[-:]\+.*\[[^]]*\]\s*\('`; `git -C WT show HEAD:FILE | sed -n 'L,L+4p'`; keep uncaptured one-call bodies forwarding parameters in order. `git -C WT grep -n -E '\b<slot>\b' HEAD -- FILE`; `git -C WT grep -n -A1 'using ALIAS' HEAD -- FILE`; `git -C WT grep -n 'CALLEE(' HEAD -- h`; `git -C WT show HEAD:CALLEE_FILE | grep -n '^namespace'`. Exact types after namespace resolution = finding.
3. Shape b: `grep -nE '^\+\s*\} else \{' pr-u0.diff`; `git -C WT show HEAD:FILE | sed -n 'S,Ep'`; finding when every else assignment repeats its initializer.
4. Shape c: `grep -nE -A1 '^\+\s*struct [A-Za-z_0-9]+[^;]*\{\s*$' pr-u0.diff | grep -E '^[0-9]+[-:]\+\s*public:'`.
5. Shape d: `grep -oE '^@@.*@@.*' pr-u0.diff | sort -u`; per listed function at HEAD: `auto* NAME = EXPR();` then a later `EXPR()`; pointer locals: `(*devs)[0]`.
6. Shape e: `grep -nE '^(@@|\+\s*struct [A-Za-z_0-9]+\s*\{|\+\s*(uint32_t|uint64_t|int|size_t) [a-z_]*(idx|index|_id)\s*(=[^;]*)?;|\+\s*[A-Za-z_:]+\* [a-z_]+ = )' pr-u0.diff`; keep id hits inside an added `struct NAME {`; `git -C WT grep -n 'struct POINTEE' HEAD -- h`; `git -C WT grep -n '\bMEMBER\b' HEAD -- h src`; a writer leaving the pointer null = ask only.
7. Shape f: `grep -nE -A1 '^\+\s*std::(vector|array)<' pr-u0.diff | grep -E '^[0-9]+[-:]\+\s*size_t n[a-z_]* = 0;'`; std::array/T[N] = none.
8. Shape g: `grep -nE -A2 '^-\s*(for|while) \(' pr.diff | grep -E '^[0-9]+-\+\s*\{\s*$'`; list end-of-body resets at HEAD (`memset(`, `.clear()`).
9. Shape h: `grep -nE '^\+.*\((bf16|float|uint(8|16|32|64)_t)\)\s*[a-z_]+\[[a-z_]+\]' pr-u0.diff`; `git -C WT grep -n 'using OBJ_t' HEAD -- h`; exact element-type match only.
10. One comment per shape at the first hit, question form, one-line fix in a ```suggestion block, ending 'etc'. Withdraw after an author fact.

On PR 2176 (BASE 363edb2910, HEAD 8e19ea3e62): step 2 hits h/tron/models/model.hpp:795-802 (aliases :627-634; callees h/tron/gof.hpp:85-97, `namespace tron::hardware` :21) = one comment at :795 ending 'etc'; :805-806 call a member on `get_device_dma_tracker()` = no finding. Steps 3-9: 3 `} else {` in h/pos/hwattention_dump.hpp, none redundant; 5 id hits, all locals; else 0.


## Check 14: disabled code left in the tree

BASE = merge base against the PR's base branch (`gh pr view N --json baseRefName`), never origin/main; if WT lacks the ref: `git -C WT log --first-parent --merges -1 --format=%P HEAD | cut -d" " -f2`.
`S='(if \(|for \(|while \(|else|\}|[A-Za-z_][A-Za-z_0-9:.>-]*(\(|\s*=\s).*[;{(,]$)'; X='([A-Za-z_][A-Za-z_0-9]*::)*(spdlog::|debug_hexdump|debug_bf16dump|debug_exit|dbg_)'`

1. Added `#if 0` and commented statements:
```
git -C WT diff -U0 BASE HEAD | awk '/^\+\+\+ /{f=substr($2,3); next} /^@@/{split($3,a,/[,+]/); n=a[2]-1; next} /^\+/{n++; print f":"n":"substr($0,2)}' \
| grep -E ":\s*#\s*if\s+(0|false)\s*$|:\s*//\s*$S" | grep -v -E "//\s*$X" \
| grep -v -E '//[^;{(,]*([a-z]+ ){3,}[a-z]+' | grep -v -E '^t/[^:]*:[0-9]+:\s*//' > disabled.txt
```
2. Removed lines reappearing commented:
```
git -C WT diff -U0 BASE HEAD | awk '/^diff --git/{f=$3} /^\+[ \t]*\/\//{l=$0; sub(/^\+[ \t]*\/\/[ \t]*/,"",l); print f"\t"l}' \
| while IFS=$'\t' read -r f l; do git -C WT diff -U0 BASE HEAD -- "${f#a/}" | grep -E '^-[^-]' | sed -E 's/^-[ \t]*//' | grep -qxF -- "$l" \
  && echo "$l" | grep -qE "^$S" && echo "$l" | grep -qvE "^$X" && echo "REAPPEARS in ${f#a/}: $l"; done
```
3. Unchanged `#if 0` within 20 lines of a hunk, h/ and src/, minus step 1:
```
for f in $(grep -E '^(h|src)/' prfiles.txt); do s=$(git -C WT diff -U0 BASE HEAD -- $f | grep '^@@' | sed -E 's/^@@ -[0-9,]+ \+([0-9]+).*/\1/' | tr '\n' ' '); git -C WT show HEAD:$f | grep -n -E '^\s*#\s*if\s+(0|false)' | cut -d: -f1 | awk -v s="$s" -v f=$f 'BEGIN{n=split(s,h," ")} {for(i=1;i<=n;i++) if ($1-h[i]<=20 && h[i]-$1<=20){print f":"$1; break}}'; done | grep -v -x -F -f <(cut -d: -f1,2 disabled.txt)
```
4. Per block: LIVE-AT-BASE when its first statement exists at BASE:
```
first=$(git -C WT show HEAD:FILE | awk -v s=LINE 'NR>s && /^\s*#endif/{exit} NR>s && !/^\s*([{}]|\/\/.*)?\s*$/{print; exit}'); git -C WT show BASE:FILE | grep -qxF -- "$first" && echo LIVE-AT-BASE || echo NEW
```
5. Live twin, two lines above, replies:
```
git -C WT show HEAD:FILE | grep -n 'NAME'; git -C WT show HEAD:FILE | sed -n "$((LINE-2)),$((LINE-1))p"
gh api --paginate repos/positron-ai/tron/pulls/N/comments --jq '.[] | select(.path=="FILE") | [.id,.user.login,.in_reply_to_id,.original_line] | @tsv'
```
6. One finding per file; later hits "same at :L".

On PR 1997 (ae5f6faec0..d306b805ce): step 1 hits h/pos/hwattention.hpp:703 `// if (pdc + 1 == dev->num_fetchers) {` and :706 `//}`, both REAPPEARS in step 2, live `wait_for_hbm_vwrite_complete(...)` at :704-705 (2771711406). PR 4557: nothing.


## Check 14: declaration, constant, include or growing function out of place

Setup: `BASE=$(git -C WT merge-base HEAD origin/$(gh pr view N --json baseRefName -q .baseRefName))`; merged PR: `BASE=$(git -C WT rev-parse $(gh pr view N --json commits -q '.commits[0].oid')^)`.

1. `git -C WT diff --name-only BASE HEAD -- 'h/*.hpp' > hdrs.txt`; skip config.hpp files and PR-added headers (`--diff-filter=A`).
2. Per header F: `git -C WT show HEAD:F > full/F; first=$(grep -n -E '^(struct|class|union|template|inline|static|constexpr|[A-Za-z_][^;]*\))[^;]*\{ *$' full/F | grep -v -E '^[0-9]+:(namespace|extern|enum)' | head -1 | cut -d: -f1); grep -n -E '^(static |inline )*constexpr [^=(]*=' full/F | awk -F: -v f=$first '$1>f'`; fire only if `git -C WT diff -U0 BASE HEAD -- F | grep '^-.*constexpr'` prints.
3. `git -C WT diff -U0 BASE HEAD -- 'h/*.hpp' | grep -E '^(\+\+\+|@@|[-+](extern|inline|struct|class|enum|template|[A-Za-z_:<>]+ [A-Za-z_]+\())'`; drop `+` lines with a `-` twin. Per symbol S: `git -C WT grep -l -E "^[A-Za-z_][A-Za-z_:<>*& ]*[ *&:]S\(" HEAD -- src`; for src/<dir>/<base>.cpp fire only if `git -C WT cat-file -e HEAD:h/<dir>/<base>.hpp` succeeds and it is not the receiving header.
4. `git -C WT diff -U0 BASE HEAD | grep -E '^\+#include "' | sed -E 's/.*"([^"]+)".*/\1/' | sort -u | while read p; do git -C WT cat-file -e HEAD:h/$p 2>/dev/null || git -C WT ls-tree -r --name-only HEAD | grep -q "$(basename $p).in$" || echo "third-party quoted: $p"; done`.
5. <fn> length at commit C: `git -C WT show C:<file> > w.cpp; s=$(grep -n -E '^ *[A-Za-z_][^;]*\b<fn>\(' w.cpp | head -1 | cut -d: -f1); ind=$(sed -n "${s}p" w.cpp | sed -E 's/^( *).*/\1/'); e=$(awk -v s=$s -v ind="$ind" 'NR>s && $0 == ind"}" {print NR; exit}' w.cpp); echo $((e-s+1))`. Map `@@` starts to the if or else branch.
6. `grep -c -E '^(inline |static )?[A-Za-z_:<>*&]+ (dump_|debug_)[a-z_]*\(' full/F`.
7. `gh api repos/positron-ai/tron/pulls/N/comments --paginate | jq -r '.[] | select(.path=="F") | select(.user.login | test("\\[bot\\]") | not) | [.id,.user.login,.in_reply_to_id,.body] | @tsv' | grep -i -E 'move|config\.hpp|next (phase|iteration)'`. Another reviewer's move request or an author-scheduled split closes the item.

On PR 2980 (BASE f59334dc24, HEAD edec446b76): step 3 fires on `pos_driver_register_fuse_stats` at h/pos/alloc.hpp:234 (defined at src/pos/device.cpp:595); step 4 at 247c8a4c22 prints `spdlog/spdlog.h` (src/pos/device.cpp:12, sibling :18); step 5: hw_prepare 467 lines at BASE (src/pos/worker.cpp:1131), 601 at HEAD, +54/+80 in the if/else branches, closed by 3405422090.


## Check 25: behavior change presented as a refactor or debug-value revert

BASE: `gh pr view N --repo positron-ai/tron --json baseRefOid -q .baseRefOid`; moved base: `git -C WT merge-base HEAD origin/<baseRefName>`.
1. `git -C WT diff -U0 BASE HEAD -- h src > c25.diff`; `python3 -I step1.py c25.diff`:
```
import sys,re
from difflib import SequenceMatcher as S
T=re.compile(r'\w+|\S');H=[];h=0;f='';K=0
for l in open(sys.argv[1],errors='replace'):
 if l[:4]=='--- ':continue
 if l[:4]=='+++ ':f=l[6:-1]
 elif l[:2]=='@@':h={'f':f,'n':re.search(r'\+(\d+)',l)[1],'o':[],'a':[]};H.append(h)
 elif h and l[0]in'-+':h['o' if l[0]=='-' else 'a'].append(l[1:].strip())
C=('//','*','/*');X=('.hpp','.cpp','.h','.cc')
for h in H:
 o,a=' '.join(h['o']),' '.join(h['a'])
 if not h['o']or not h['a']or h['f'][:2]=='t/'or not h['f'].endswith(X)or all(s.startswith(C)for s in h['o']+h['a']):continue
 r=d=0
 for t,i,j,k,m in S(a=T.findall(o),b=T.findall(a),autojunk=False).get_opcodes():
  if t!='equal':r+=j-i;d+=m-k
 if 0<r+d and r<=2 and d<=8:K+=1;print(h['f'],h['n'],r,d,o,'->',a)
print('kept',K)
```
Drop: string edits, argument lists, type swaps, `#if`/`#define`, diff-declared names, typedef wraps, same-value constants, inserted statements.
2. `grep -n -E '^-.*(isnan|isfinite|isinf|infinity\(\))' c25.diff`; per hit `git -C WT grep -n -F -- '<removed line>' HEAD -- h src` (hit = move); else evaluate the new compare for NaN.
3. `grep -n -E '^\+\s*//\s*(usleep|sleep|nanosleep|wait\w*|mwaitx|TRON_ASSERT|assert|lock|unlock|check\w*)\s*\(' c25.diff`; `grep -c -F '+  <call text>' c25.diff` (hit = moved).
4. `grep -E '^[-+]\s*(inline )?(static )?constexpr' c25.diff | sed -E 's/^([-+]).*\b(\w+)\s*=\s*([0-9]+).*/\1 \2 \3/' | awk '{k=$2; if($1=="-") o[k]=$3; else n[k]=$3} END{for(k in o) if(k in n && o[k]!=n[k]) print k, o[k], "->", n[k]}'`; `git -C WT grep -n '<constant>' HEAD -- h src`; class readers fatal or log-only.
5. `grep -n -E '^[-+].*(DEFAULT_ON|_DEFAULT|_ENABLED|DEFAULT).*(!=|==) *[01]\b' c25.diff`; `git -C WT show HEAD:<file> | sed -n '<line-15>,<line>p'`; `grep -n '<MACRO>' doc/*.md`.
6. `git -C WT grep -n -E '<old container>;|<new container>;|struct <type>|<new container>.push_back' HEAD -- h src`.
7. `grep -n -i -E '<old token>|<new token>|intention|deliberate|debug-only|revert' body.md` (clears); `git -C WT log --format='%h %s%n%b' BASE..HEAD | grep -n -i -E '<old token>|<new token>'` (never clears).
On PR 2176 (363edb2910..429249ead6): 22 kept; h/tron/models/self_attention.hpp:859-860 `.i` -> `token_positions[...]`; body 0 hits; commit 1fd45e6062 quoted, not cleared.


## Check 26: count, index or completion wait must cover its set

0. cd WT; BASE=$(git merge-base HEAD origin/$(gh api repos/positron-ai/tron/pulls/N --jq .base.ref)) (merged PR: --jq .base.sha). Not origin/main.
1. git diff -U0 BASE HEAD -- h src > pr-u0.diff
2. python3 -I - < pr-u0.diff <<'EOF'
import re,sys
f=None;n=0
for i,l in enumerate(sys.stdin,1):
 m=re.match(r"^@@ -\S+ \+(\d+)",l)
 if l.startswith("+++ "): f=l[6:].strip()
 elif m: n=int(m.group(1))
 elif l.startswith("+"): print(i,f+":"+str(n)); n+=1
EOF
3. (a) grep -nE '^\+.*[a-z_]+ *= *[a-z_]+\.size\(\)|^\+.*(num|n)_?[a-z_]* *= *[0-9a-z_]+ \* [a-z_]+' pr-u0.diff; grep -nE 'std::array<[^>]*, *[A-Za-z_:0-9]+>|\[[A-Z_][A-Z_0-9]*\]' pr-u0.diff
4. (b) grep -nE '^\+\s*break;|^\+\s*(early_release|early_exit|release_early)\b' pr-u0.diff
5. (c) grep -nE '^\+\s*(uint(8|16|32|64)_t|int|size_t|auto) +[a-z_]+ *= *(0|-1|nullptr|std::numeric_limits)[^x0-9]' pr-u0.diff
6. (d) grep -nE '^\+\s*[a-zA-Z_:>.-]*(wait|join|flush|sync)[a-z_]*\([^;]*\);' pr-u0.diff | grep -vE '^[0-9]+:\+\s*(extern|inline|static|void|bool|int|auto)\b'
7. (e) grep -nE '^\+.*(get_device\(([0-9]+|process_device_id\{[0-9]+\})\)|(devices|devs|instances|ranks|shards|queues)[a-z_]*(\(\))?\)*\[0\]|\.front\(\))' pr-u0.diff
8. (a) git grep -n '<CAP> *=' HEAD -- h; git grep -n '<count> *=' HEAD -- h src; git show HEAD:<file> | sed -n '<assign>,<first indexed write>p' | grep -nE 'TRON_ASSERT|<= *<CAP>|< *<CAP>|return'
9. (b) git show HEAD:<file> | sed -n '<loop start>,<loop end>p' | grep -nE 'break;|return|<count> *='; git grep -n '<out-param>' HEAD -- src h
10. (c) git show HEAD:<file> | awk '/<helper signature>/,/^}/' | grep -nE 'return .*<name>|\.<field> *= *<name>|<name> *='; git grep -n '<stored field>' HEAD -- src h
11. (d) git show HEAD:<file> | awk '/<callee signature>/,/^}/'; git grep -nE 'void <wait fn>\(' HEAD -- src; git grep -n '<wait fn>(' HEAD -- h src
12. (e) git grep -nE 'pos_list_devices\(\)|get_num_devices\(\)' HEAD -- h src; git grep -nE 'using tp[24] = ' HEAD -- h/tron/models/common.hpp
13. grep -nE '^\+.*<= *\([a-z_]+ */ *[a-z_]+\) *\* *[a-z_]+' pr-u0.diff
14. gh api repos/positron-ai/tron/pulls/N/comments --paginate | jq -r '.[] | select(.in_reply_to_id!=null) | [.user.login,.body] | @tsv' | grep -iE 'next pass|upcoming PR|future|phase' | grep -v '\[bot\]'

On PR 2011 (BASE ab75e61d83, HEAD d4795f37a5): step 6 hits h/pos/hwattention.hpp:645 and :674 `wait_for_xfer_blocks(get_device(0), xfer)` after loops at :635 and :666; src/pos/driver.cpp:912 checks xfer.queue, dev unused (:892); deferral 2790051381.


## Check 27: silent fallback where an assert belongs

0. `B=$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName); BASE=$(git -C WT merge-base HEAD origin/$B)`; if BASE = HEAD: `BASE=$(git -C WT rev-parse $(gh pr view N --repo positron-ai/tron --json commits -q '.commits[0].oid')^)`. WT lacks HEAD: `gh pr diff N`; `gh api "repos/positron-ai/tron/contents/<path>?ref=HEAD" --jq .content | base64 -d`. `D="git -C WT diff -w -U0 BASE HEAD -- h src"`.
1. Clamps: `$D | grep -n -E '^(\+\+\+|@@|\+.*std::(min|max|clamp)<?[^;]*,\s*(\w+\()?([A-Z_]*(MAX|SIZE|LIMIT)[A-Z_]*|[0-9]+)\)?\);)'`
2. Exits: `$D | grep -n -E -A2 '^(\+\+\+|@@|\+ *if \(.*(<|>|<=|>=|==|!=|!\w)|\+ *return nullptr;)' | grep -E '^[0-9]+[:-](\+\+\+|@@|\+ *if .*(return|continue|break)|\+ *(return[^;]*;|continue;|break;))'`; `$D | grep -n -E '^\+ *if \(\w+ < \w+(\.size\(\))?( &&| \|\|)'`
3. Self-move: `$D | grep -n -E '^\+.*this != &other'`; `git -C WT grep -n -E 'std::move\(.*<Type>|vector<<Type>>' HEAD -- h src`
4. Sentinels: `$D | grep -n -E '^\+ *if \(\w+ == 0\)|^\+ *if \(!\w+\)'`; `git -C WT show HEAD:<file> | sed -n '<start>,<end>p' | grep -n -E 'xfer_blocks|descriptor|\.fields\.|debug_exit|spdlog::error|TRON_ASSERT'`
5. Waits: `$D | grep -n -E -A3 '^\+ *(while ?\(|for ?\(;;\)|do \{)'`; `git -C WT grep -n -E '<flag>\.store\(' HEAD -- src h`; `git -C WT log --format='%h %ad %s' --date=short -S'<flag>' -- <file>`; `git -C WT show HEAD:src/pos/worker.cpp | grep -n 'max_checks\|deadline = \|debug_exit'`; `git -C WT grep -n -E 'wait_for_|delay_ns' HEAD -- h/system/mwaitx.hpp`
6. Asserts: `$D | grep -n -E -A2 '^\+.*TRON_(ASSERT|ABORT)\('`; `git -C WT grep -n 'define TRON_ASSERT(' HEAD -- h`
7. Tells: `$D | grep -n -i -E '^[-+].*//.*(unit tests?|test states?|defensive|just in case|sanity|prevent(s)? reuse|we will expect|for now|today|eventually|extend)'`
8. Reach: `git -C WT grep -n '<LIMIT>' HEAD -- h src`; `git -C WT grep -n -E 'TRON_ASSERT[A-Z_]*\(.*<param>' HEAD -- h src`; `git -C WT grep -n -E '_eligible\(|is_supported\(|can_use' HEAD -- h`; `git -C WT grep -n '<function>(' HEAD -- h src t`; `git -C WT show HEAD:<file> | grep -n -A3 '<callee>(size_t'`; `git -C WT grep -n '<hook>' HEAD -- t/`

On PR 4007 (HEAD 29a39ac33e, BASE 21162f5568): step 1 hits h/pos/hwattention.hpp:466, :990, :1035; step 8 finds h/tron/models/model.hpp:789-795 (bool screen), src/tron/gof.cpp:195-196 and model.hpp:1571-1573 (assert the value): 3866435051. On PR 4596 (HEAD 1430736b2a): step 2 hits h/tron/models/attn_stats.hpp:382-383, :409, :421; row() :327-329 asserts both bounds: 4125033677.


## Check 28: Shared state: new thread, misplaced lock, double read, or dropped wait

1. `BASE=$(git -C WT merge-base HEAD origin/$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName))`
2. HEAD: `gh api repos/positron-ai/tron/pulls/N/reviews --jq '.[]|select(.user.login=="Wado-posi")|[.submitted_at,.commit_id]|@tsv'`; if `git -C WT cat-file -t HEAD` fails: `gh api repos/positron-ai/tron/contents/<path>?ref=HEAD --jq .content | base64 -d`
3. `git -C WT diff BASE HEAD -- h src ':!h/tron/threading.hpp' | grep -v -E '^\+\s*//' | grep -n -E '^\+.*(parallel_for|std::thread|std::jthread|std::async|std::mutex|lock_guard|unique_lock|scoped_lock|std::atomic|fetch_add)'`
4. `git -C WT diff BASE HEAD -- h src | grep -v -E '^[-+]\s*//' | grep -n -E '^[-+].*(_needed|_ready|ready\(|visible\(|depends)'`
5. `git -C WT diff BASE HEAD -- h src | awk '/^\+\+\+ /{f=substr($2,3)} /^@@/{split($3,a,","); n=substr(a[1],2)+0; next} /^-/{next} {if ($0 ~ /^\+.*(parallel_for|std::thread|std::mutex|lock_guard|std::atomic|fetch_add|_needed|_ready)/) print f":"n": "substr($0,2); n++}'`
6. `git -C WT grep -n '<region fn>' HEAD`; `git -C WT grep -n -E '\b<callee>\(' HEAD -- h src`; `git -C WT show HEAD:<def file> | sed -n '<s>,<e>p' | grep -n -E 'mutex|lock_guard|atomic|wait_for|usleep|delay_ns|while|do \{'`
7. `git -C WT show HEAD:<file> | sed -n '<decl-3>,<decl>p'`; `git -C WT grep -n '<mutex>' HEAD -- h src`; `git -C WT grep -n '<member>' HEAD -- h src t`; `git -C WT grep -n -E '&[A-Za-z_]+::<member>' HEAD -- src`; `git -C WT show HEAD:<owner header> | grep -n 'std::mutex'`
8. `git -C WT diff BASE HEAD | grep -n -E '^\+.*(count_complete_gofs|dma_complete)\(\)|^\+.*\.load\('`; `git -C WT grep -n -B2 -A2 '<getter>' HEAD -- h | grep -i -E 'race|async'`; `git -C WT grep -n -E '= [a-z_.]*<getter>\(\);' HEAD -- h src`; `git -C WT log --format='%h %an %ad %s' -S'<getter>' BASE -- <file>`
9. `git -C WT diff BASE HEAD -- <file> | grep -n '<removed wait name>'`; `git -C WT diff BASE HEAD -- <file> | grep -n -A14 '<predicate>('`; `git -C WT grep -n -E 'scaled_v|entire page|whole page' HEAD -- h/tron/models/kv_cache.hpp`; `git -C WT grep -n -l '<predicate>\|poison\|NaN' HEAD -- t/`

On PR 2777 (b556b5527957, BASE 743de0311b59): step 3: h/tron/models/model.hpp:57-73, h/tron/hardware/tensor.hpp:61-62; step 6: tensor.hpp:417 -> :94 -> src/pos/driver.cpp:1007 `set_hardware_weights` writes `load_weight_q`; step 7: `PosDevice` owns `inwork_mutex` h/pos/device.hpp:212, `wait_for_xfer_blocks` driver.cpp:966-994 writes nothing = 3277240111; at 4840c99a534e = 3275212298.


## Check 14: buffer lifetime and alignment follow the consumer

Setup: `BASE=$(git -C WT merge-base HEAD origin/$(gh pr view N --json baseRefName -q .baseRefName))`. Force-pushed head: `gh api "repos/positron-ai/tron/contents/<path>?ref=HEAD" -q .content | base64 -d`.

1. `grep -nE '^\+[^/]*(dma_allocate|dma_deallocate|release_buffer|free_staging|abandon\(|\.pop\(\)|\.reset\(\)|xfer_(n_)?blocks\(|xfer_gofs?\(|dma_tracker::push|~[a-z_]+\(\)\s*\{)' pr.diff`
2. `git -C WT grep -n -E 'clear\(\)|~dma_tracker|q\.pop\(\)|\.reset\(\)|std::optional<pending_xfer>' HEAD -- src/pos/dma_tracker.cpp h/pos/dma_tracker.hpp`; each path waits, leaks or frees.
3. `git -C WT grep -n -E 'reservation\.commit\(\)|guard\.commit\(\)|\.push\(pending_xfer' HEAD -- h src`
4. `grep -nE '^\+.*\.reserve\([0-9]+\)' pr.diff`; per container V: `grep -nE '^\+.*&\s*[a-z_]+\s*=\s*V(\.(back|front)\(\)|\[)|= *V\.data\(\)' pr.diff`; `grep -nE '^\+.*V\.(push_back|emplace_back|insert|resize|assign|pop_back)\(' pr.diff`
5. `git -C WT show HEAD:<file> | sed -n '<ref line>,<last use>p' | grep -n -E 'V\.(push_back|emplace_back|insert|resize|assign|pop_back)\(|continue;|break;|return'`
6. `git -C WT diff BASE HEAD -- h src | grep -nE '^\+.*(std::array<(bf16|float|uint8_t|__m256i|__m512i), *[A-Za-z_0-9]+>|^\+\s*(bf16|float|uint8_t) [a-z_]+\[)' | grep -v alignas`
7. `git -C WT grep -n '<member> =' HEAD -- h src t`; `START=<signature line>; END=$(awk -v s=$START 'NR>s && /^}/ {print NR; exit}' <file>); sed -n "${START},${END}p" <file> | grep -n -E '_mm256_(store|load)_si256|_mm512_(store|load)_(si512|ps|epi)|_mm512_stream'`
8. `git -C WT grep -n -E '^(struct|class) <T>\b' HEAD -- h`; `git -C WT show HEAD:<file> | grep -n alignas`; `git -C WT grep -n -E '<consumer>\(' HEAD -- t/`
9. `grep -o -m1 avx2 /proc/cpuinfo`; `g++ -O1 -mavx2 -fsanitize=alignment -fno-sanitize-recover=alignment repro.cpp` (`array + 8` of an `alignas(64)` array).

On PR 4128 at 97de6ee02c (BASE 130ad3a652): step 6 src/tron/gof.cpp:436 `v_scratch`, passed :445, consumer h/tron/models/kv_cache.hpp:2096, `_mm256_store_si256` :2109; bf16.hpp:12-13 2 bytes; sibling alignas gof.cpp:371; t_phase1_integration.cpp:890 copies. Step 2: `~dma_tracker` :58-68 calls clear() :67, clear() waits :180; at 442ed0dd1a `~dma_tracker` :57-61 skips clear(), `~gof_dma_batch` gof.cpp:40-42 frees. Step 3: gof.cpp:488, :511. On PR 2499 at 54a6fd7d1c (BASE 9ef4586a57, hwattention_sync): step 4 h/tron/scheduler/full.hpp:1395 `stk.reserve(64)`, refs :1403, :1956; step 5: push :1850, `break` :1854, `continue` :1858, pop :1953, re-take :1956; finding = question.


## Check 30: avoidable per-call work on a per-token, per-layer or spin path

0. `HEAD=$(gh api repos/positron-ai/tron/pulls/comments/<id> --jq .original_commit_id)`; `BASE=$(git -C WT merge-base HEAD $(gh api repos/positron-ai/tron/pulls/N --jq .base.sha))`. No HEAD: `gh api repos/positron-ai/tron/compare/BASE...HEAD`, `gh api -H 'Accept: application/vnd.github.raw' repos/positron-ai/tron/contents/<file>?ref=HEAD`.
1. `git -C WT diff -U0 BASE HEAD -- 'h/*' 'src/*' | grep -n -E '^(\+\+\+|@@|\+)' | grep -v -E '^[0-9]+:\+\s*(//|\*)' | grep -E '^[0-9]+:(\+\+\+|@@|\+.*(std::vector|\.reserve\(|std::map|std::memset|std::fill|std::sort|make_shared|make_unique|[^a-z_]new |std::function|_fn\(|TRON_ASSERT[A-Z_]*\([^,]*[a-z_0-9]\(|release_buffer|free_|evict|deallocate))'`; drop src/pos/fake.cpp. Enclosing function (.cpp `RX='^[a-zA-Z_][^;]*\([^;]*$'`, header `RX='^ {2,4}[a-zA-Z_][^;=]*\([^;]*$'`): `git -C WT show HEAD:<file> | grep -n -E "$RX" | grep -v -E '^[0-9]+:\s*(return|if|for|while|else|switch|TRON_|TRACE_|static_assert|using|namespace|template|//|#|auto |constexpr)' | awk -F: -v L=<L> '$1<=L{l=$0} END{print l}'`.
2. `git -C WT diff -U1 BASE HEAD -- 'h/*' 'src/*' | grep -n -A1 -E '^\+\s*(static const |const )?[a-zA-Z_0-9:<>]+ [a-z_0-9]+ = .*[a-z_0-9]\(.*\).*;\s*$' | grep -B1 -E '^[0-9]+-\+?\s*(if|else if) \(' | grep -v '^--$'`; keep functions matching `wait|poll|spin|monitor|for_event`.
3. `git -C WT grep -n -E '<fn>\(' HEAD -- h src | grep -v -E '^\S+:\s*//'`; classify by the loop 15 lines above: `load(std::memory_order_acquire)` spin, `for (.*layer`, `for (.*job|token`, `poll_completions`, `monitor_and_wait`, `run_forward` once, startup. Sibling: `git -C WT grep -n -E '<stem>s?\(|<stem>_batch\(' HEAD -- h src`.
4. `git -C WT grep -n -E '(hwkv_coalesce_tokens|gof_tokens|FETCHERS_PER_DEVICE|HWCACHEBLOCK_BYTES|POS_DATA_SIZE)\s*=' HEAD -- h`; layers from the model the body names.
5. `git -C WT show BASE:<file> | sed -n '<start>,<end>p'`; `git -C WT show HEAD:<file> | grep -n -E 'std::array|[a-z_]+\[[0-9A-Z_]+\];|std::fill|std::sort|<callback>\('`; `git -C WT grep -n -E '<callback>\s*=' HEAD -- h src` (copy = gather); `git -C WT grep -n -F '<condition>' HEAD -- h src`.

On PR 4128 at 442ed0dd1a (BASE 9a905763ac): model.hpp:2973-2974 vector before `try_dequeue` :2977 (spin self_attention.hpp:904), :2993-2994 (BASE :2978-2987 allocated nothing); gof.cpp:37 memset, :255-256 vectors vs xfer_gof arrays :186-197, :278 sort, :333 v_head_fn (full.hpp:2506 copies); model.hpp:3023-3030 and :3110-3116 same assert; PR 2903 mwaitx.cpp:112 above :118; PR 2906 gof.hpp:224.


## Check 31: one owner per record, one gate per subsystem, one stable row key

0. `B=$(gh pr view N --json baseRefName -q .baseRefName); BASE=$(for c in $(git -C WT rev-list --first-parent origin/$B); do git -C WT merge-base --is-ancestor $c HEAD && echo $c && break; done)`
1. `git -C WT diff -U0 BASE HEAD -- h src | grep -n -E '^(\+\+\+|@@|\+.*(fetch_add|inc_relaxed|max_relaxed|\.store\(|\|= ))' | grep -v -E '^[0-9]+:\+.*(out|s|json) \+='`; `git -C WT grep -n -E '(INSTANCE|ARRAY\[[^]]*\])\.(M1|M2|M3)' HEAD -- h src`; `git -C WT show HEAD:FILE | awk -v L=LINE 'NR<=L && /^  [a-z][a-z_0-9<>:& ]* [a-z_0-9]+\(/ && !/^  (if|for|while|switch|return)\b/ {f=$0; n=NR} END{print n": "f}'`
2. `git -C WT grep -n -E 'state\.forward\(|\.run_forward\(|begin_forward\(|end_forward\(|note_forward_wall\(' HEAD -- h src t`; `git -C WT show HEAD:FILE | grep -n 'current_class'`
3. `git -C WT diff -U0 BASE HEAD | grep -n -E '^\+.*(if constexpr|getenv\(|_enabled\(\)|_configured\(\)|_configure\()'`; `git -C WT grep -n -E 'tron::hardware::gof_[a-z_]+\(' HEAD -- h src`; `git -C WT show HEAD:src/tron/gof.cpp | grep -n -E '/ gof_n_layers|% gof_n_layers|gof_n_layers = 0'`
4. `git -C WT diff -U0 BASE HEAD | grep -n -E '^\+.*(attn\.size\(\)|num_workers\(\)|std::vector<[a-z_]+>\(N_)'`; `git -C WT grep -n -E '\.resize\(n_attn_workers\)' HEAD -- h`; `git -C WT grep -n -E '(note_attn_job|note_join_wait|add_visits|token_path_span|[^a-z_]row)\(' HEAD -- h`; `git -C WT grep -n -E 'num_workers\(\) - n_attn_workers|pool_worker\(|recommend_n_main_helpers' HEAD -- h`
5. `git -C WT diff -U0 BASE HEAD | grep -n -E '^\+.*(\? [a-z_:]+_class::|\.size\(\) >= [a-z_]+_tokens|== [a-z_]+\.size\(\))'`; `gh api graphql -f query='{repository(owner:"positron-ai",name:"tron"){pullRequest(number:N){userContentEdits(first:50){nodes{editedAt diff}}}}}' | grep -i -E 'runtron|rinzler'`; `git -C WT show HEAD:h/tron/scheduler/full.hpp | grep -n -E 'compute_forward_args\(|attempt_kv_job\(|ensure_listener\('`; `git -C WT show HEAD:README.stats.md | grep -n -i 'decode_like'`

On PR 4596 (1430736b2a, BASE 66c7bb8db1): forward_counters attn_stats.hpp:244-249, writes :439-441 :461 :463 :471, caller full.hpp:2100-2103, begin/end_forward model.hpp:1745-1750, rows self_attention.hpp:496-498, index :855 :1315 :1652, pool thread model.hpp:1721-1722, fold attn_stats.hpp:526; predicate model.hpp:1746, full.hpp:2242, README.stats.md:246. PR 2176 (635de61895): guard model.hpp:773, unguarded gof_on_save_k :1419, gof.cpp:53 :191. PR 4128 (442ed0dd1a): budget model.hpp:2970-2975.


## Check 32: new path, state, counter or option visible through existing operator tools

1. `BASE=$(git -C WT merge-base HEAD origin/$(gh pr view N --json baseRefName -q .baseRefName))`; merged PR (merge-base returns HEAD): `BASE=$(gh api repos/positron-ai/tron/pulls/N/commits --jq '.[0].parents[0].sha')`.
2. Comment HEAD: `gh api repos/positron-ai/tron/pulls/comments/<id> --jq '.original_commit_id'`; absent from WT: `gh api "repos/positron-ai/tron/contents/<path>?ref=<sha>" --jq .content | base64 -d`.
3. Members: `git -C WT diff -U0 BASE HEAD -- 'h/*.hpp' | grep -n -E '^(\+\+\+|@@)|^\+\s+[^/(]+\s[a-z_][a-z0-9_]*(\s*=[^;]*|\{[^}]*\})?;'`. Helper: `F=$(mktemp); git -C WT show HEAD:<file> > $F; grep -n -E 'std::string (debug_string|to_string|dump)\(|operator<<\(' $F; sed -n '<helper>,<end>p' $F > body.txt; for m in <members>; do echo $m $(grep -c $m body.txt); done`.
4. Trace: `git -C WT diff --diff-filter=A --name-only BASE HEAD -- src`; `for f in $(git -C WT ls-tree --name-only HEAD <dir>); do echo "$f $(git -C WT show HEAD:$f | grep -c TRACE_EVENT)"; done`; `git -C WT diff BASE HEAD -- src h | awk '/^\+.*\)( const| noexcept)* \{$/ {fn=$0} /^\+.*for \(/ {loop[fn]=1} /^\+.*(lock_guard|unique_lock|scoped_lock)/ {lock[fn]=1} END {for (f in loop) if (lock[f]) print f}'`; `git -C WT diff BASE HEAD -- src h | grep -c -E '^\+.*(TRACE_EVENT|TRACE_COUNTER|TRON_CHECKPOINT)'`; `git -C WT grep -l 'perfetto::Category(' HEAD -- h`.
5. Counter: `git -C WT diff BASE HEAD | grep -n -P '^\+.*(option\(TRON_|#ifdef TRON_(?!FUSE|PERFETTO)|#if TRON_)'`; `git -C WT diff BASE HEAD | grep -n -E '^\+.*(fprintf\(stderr|report_at_exit|~[a-z_]+\(\) \{)'`; `git -C WT show HEAD:h/system/fuse_stats.hpp | grep -n -E 'make_file|set_read_callback'`.
6. Launcher: `git -C WT diff BASE HEAD -- src/runtron.cpp src/rinzler.cpp | grep -n -E '^\+\s*\("[a-z-]+",|requires --'`; `git -C WT grep -n -E '"\$RUNTRON"|gen/runtron' HEAD -- perfetto bin ci`; per launcher `grep -n -F -- '--<coupled>'` and `grep -n -F -- '--<new flag>'`.
7. Sample, measurement: `grep -n -E '!\[|```|before|after|rebuild|TPS' body.md`; `grep -n -E '/home/|/var/tmp/|/scratch/' body.md` hits never count (check 9).

On PR 2980 (HEAD edec446b76, BASE f59334dc24): step 3 lists enum PrevCmdKind h/pos/device.hpp:393 and ten members :394-405; PosDevice::debug_string :493, body :493-590, 0 hits per member. Steps 4-6: 0 trace macros, awk empty, gate list empty, counters in FUSE at src/pos/device.cpp:626-642, 0 option rows. PR 4267 (ef13273ba9) fires at CMakeLists.txt:47 and page_share_counters.hpp:124.


## Check 1: value-pinning rows, fixture placeholders and opaque literals need a consumer or provenance

BASE: `BASE=$(git -C WT merge-base HEAD $(gh api repos/<org>/<repo>/pulls/N --jq .base.sha))` (PR base branch, not origin/main). Steps 1-8 unchanged.

9. Kind (b): `git -C WT diff -U0 BASE HEAD -- 't/*' 'tests/*' | awk '/^\+\+\+ /{f=substr($2,3); next} /^@@/{split($3,a,/[,+]/); n=a[2]; next} /^\+/{ if ($0 ~ /^\+[ \t]*[A-Za-z_][A-Za-z_0-9]*(\.|->)[A-Za-z_][A-Za-z_0-9]*[ \t]*=[ \t]*(1\.0f?|0\.0f?|[0-9]+)[ \t]*;[ \t]*$/) print f":"n": "$0; n++; next}'`. Skip literals present at BASE and positional arguments.
10. Callee: `grep -n -E '&<var>\b|<var>\)' full/<file>`; `git -C WT grep -n '<callee>' HEAD -- h src`; hardware file, not src/pos/fake.cpp: `git -C WT show HEAD:<file> | grep -n -E '<param>->|\.<field>'`. Record READ/unreached/NEVER READ.
11. Producer: `git -C WT grep -n '<field>' HEAD -- h src`; evaluate on the fixture's values. NEVER READ and unequal = placeholder.
12. Repeats: `grep -n '<field> = <literal>' full/*`; one finding, other files second line.
13. Kind (c): `grep -n -E '^\+.*(\b(REQUIRE|CHECK)[A-Z_]*\(|\bassert\b)[^/]*\b[0-9a-f]{32,}\b' pr.diff`; `grep -n -E '^\+.*(\b(REQUIRE|CHECK)[A-Z_]*\(|\bassert\b).*\[(\s*0x[0-9a-f]+\s*,){3,}' pr.diff`; `grep -n -E '^\+\s*[A-Za-z_][A-Za-z_0-9]*\s*=\s*"[0-9a-f]{32,}"' pr.diff` then follow the name (grep -E, not awk). Review-commit file: `gh api 'repos/<org>/<repo>/contents/<path>?ref=<commit>' --jq .content | base64 -d > full/<path>`; hits: added lines, expected side only.
14. Provenance: `sed -n '<start>,<line>p' full/<file>` (to the first blank line or def/TEST_CASE); keep only generator, date, revision or copied-from file:line. `git -C WT grep -n '<first 12 hex>' HEAD -- docs doc '*.md' '*.json'`; `git -C WT show HEAD:AGENTS.md | grep -n -i -E 'regist|anchored|evidence|provenance|frozen'`, same for CLAUDE.md; missing file = "no register mandated". Register without the literal: ask origin plus row; no register: ask command, date, revision.

On PR 2176 (HEAD 635de61895, BASE 1794cdf67d) and asim 244: step 9 t/t_hwattention.cpp:93 gqa=4, :94 :571 pre_attn_scalar=1.0f, t/t_hwattention_replay.cpp:217; step 10 src/pos/hwattention.cpp:18-19, :48-49 read kv_head_size and n_kv_heads only; step 11 h/tron/models/self_attention.hpp:396 1.0f/sqrtf(128)=0.088 (placeholder), src/tron/gof.cpp:65 gqa=4 (not fired); repeats :94, :571, :1029, :1174, fixed 8a6db7243; asim tests/test_qwen35_native_reference.py:40 (3e71b6c4d4), AGENTS.md:147-149 register, row absent, fixed 927d501a86 (docs/ANCHORED_EVIDENCE.md:191).


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

Widening (2026-10-06):

## Check 3A: a test must run, reach its assertion and observe the defect

Steps 1-8 stay. BASE:
`BASE_SHA=$(gh api repos/positron-ai/tron/pulls/N --jq .base.sha); BASE=$(git -C WT merge-base HEAD $BASE_SHA)`
9. Added exits (b): `git -C WT diff -U0 BASE HEAD -- 't/*.cpp' | awk '/^\+\+\+ /{f=substr($0,7)} /^@@/{split($3,a,/[,+]/); n=a[2]-1} /^\+/ && !/^\+\+\+/{n++; if ($0 ~ /^\+[[:space:]]*(return;|SKIP\()/) print f":"n": "substr($0,2)}'`
10. Owner line: `awk -v L=<line> 'function ind(s){match(s,/^[ ]*/);return RLENGTH} {l[NR]=$0} END{h=ind(l[L]); for(i=L-1;i>0;i--){ if(l[i]~/^[ ]*$/)continue; if(ind(l[i])<h){print i": "l[i]; exit}}}' full/<file>` (TEST_CASE/SECTION owners only)
11. Bounds, hidden assertions, date: `awk -v L=<line> 'NR<=L && /^TEST_CASE/{s=NR} NR>L && /^TEST_CASE/ && !e{e=NR} END{if(!e)e=NR+1; print s, e}' full/<file>`; `sed -n '<line>,<e-1>p' full/<file> | grep -c -E '^[[:space:]]*(REQUIRE|CHECK)'`; `git -C WT log --format='%h %ad %s' --date=short -G'^  return;$' HEAD -- t/<file>`
12. Selection (c): `git -C WT diff -U0 BASE HEAD -- 't/*.cpp' | grep -E '^[-+].*TEST_CASE[_A-Z]*\(' | paste - -`; `grep -n -E '"\[\.' full/<file>`; `grep -n -i -E 'disable|hidden|\[\.' body.md log.txt`; `git -C WT show HEAD:t/CMakeLists.txt | grep -n -E '<binary>|LABELS fpga|min_slices|DISABLED'`
13. Fake (d): `git -C WT grep -n '<call>' HEAD -- h/ src/`; `git -C WT show HEAD:src/pos/fake.cpp | grep -n -A12 '<entry>('` (empty: real driver, no (d)); `git -C WT show HEAD:src/pos/fake.cpp | awk '/^[A-Za-z_].* [a-z_0-9:]+\(/{name=$0; n=NR} /^  return \{[^}]*\};$/{if (NR-n<16) print n": "name}'`; `git -C WT diff -U0 BASE HEAD -- t/<file> | grep -E '^[-+].*(REQUIRE|CHECK)'`
14. Artifacts (e): `git -C WT diff -U0 BASE HEAD -- 't/*.cpp' 't/*.hpp' | grep -n -E '^\+.*(ofstream|fopen\(|create_directories|"/tmp/|for_agent/|\.json")'`; `grep -n -F '<name>' full/<file>`; `grep -n -E 'remove\(|unlink|remove_all|temp_directory_path|mkstemp|getpid' full/<file>`
15. Lane: `for f in $(git -C WT ls-tree --name-only HEAD .github/workflows/); do git -C WT show HEAD:$f | sed -n '/^on:/,/^jobs:/p' | grep -n -A2 -E 'pull_request|push|merge_group'; done`; `gh api repos/positron-ai/tron/commits/HEAD/check-runs --jq .total_count`

On PR 1920: t/t_hwattention.cpp:670 `return;` under :603 TEST_CASE_METHOD, REQUIREs :725, :755; t_hwattention_replay.cpp:124 writes, :129 reads, 0 cleanup. PR 2011: t/t_hwattention.cpp:500 `[.save_k_and_v_to_hardware]`. PR 4128: src/pos/fake.cpp:336-346 bare return, t/t_phase1_integration.cpp:912-958. PR 4557: existing line stays at 96a6220ab6.


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

Widening (2026-10-06):

## Check 3B: A run on the changed path is named at the reviewed head

1. `gh api repos/positron-ai/tron/pulls/N --jq '"\(.base.ref) \(.base.sha)"'`; BASE=`git -C WT merge-base HEAD origin/<base.ref>` (merged: `.base.sha`).
2. `gh api repos/positron-ai/tron/commits/HEAD/check-runs --paginate --jq '.check_runs[] | "\(.name) | \(.conclusion) | \(.app.slug)"'`
3. `git -C WT show HEAD:.github/workflows/cmake-single-platform.yml | grep -n -E '^  [a-zA-Z_-]+:$|^    name:|needs:|^    if:|ctest|slice run'`; the test job is above the `ctest` or `bin/slice run` line; `sed -n '/^on:/,/^[a-z]/p'` (branch filter); never cite row `test` (label-gated test-release-build.yml).
4. `git -C WT show HEAD:<f> | grep -n -E '^#(ifdef|ifndef|if|else|elif|endif)([ \t]|$)'`
5. `git -C WT diff -U0 BASE HEAD -- <f> | grep '^@@' | sed -E 's/^@@ -[0-9,]+ \+([0-9]+).*/\1/'`; per L: `git -C WT show HEAD:<f> | awk -v L=$L 'NR>L{exit} /^#(ifdef|ifndef|if)[ \t]/{d++;n[d]=$0;s[d]=NR;next} /^#else/{n[d]=n[d] " [else@" NR "]";next} /^#endif/{d--;next} END{for(i=1;i<=d;i++) printf " > %s@%d", n[i], s[i]; print (d?"":" top level")}'`
6. `git -C WT grep -n -E 'define X|-DX' HEAD -- CMake* nix h src`; `git -C WT diff -U0 BASE HEAD -- <f> | grep '^+' | grep -o -E '[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])? *(=|\.wait|\.data)' | sort -u`; `git -C WT show HEAD:<f> | sed -n '<else>,<endif>p' | grep -n -E '<ident1>|<ident2>'`
7. `git -C WT show HEAD:t/CMakeLists.txt | grep add_catch_test | grep -E 'LIBRARIES[^)]*\b(pos|full_scheduler)\b'`.
8. R='tests passed|Running t_|ctest|runtron|validated|tested'; `grep -n -i -E "$R" body.md`; `gh pr view N --repo positron-ai/tron --json comments,reviews --jq '.comments[].body, .reviews[].body' | grep -n -i -E "$R"`; `git -C WT log --format=%B BASE..HEAD | grep -n -i -E "$R"`
9. `gh api repos/positron-ai/tron/pulls/N/comments --paginate --jq '.[] | select(.user.login|test("bot")) | select(.body|test("High Severity")) | "\(.id) \(.commit_id) line=\(.line) | \(.body|split("\n")[0])"'`; keep HEAD rows naming a runtime scenario.
10. With a labelled host and HEAD built: `ctest -L fpga` or the step-7 binaries; paste `100% tests passed, N tests failed out of M`; else `Insufficient data: <no host with label fpga | no build of HEAD>`.

On PR 2148: HEAD 8f22c93862, BASE e2ce886cca (base hwattention_sync); check-runs `test | skipped` only; `branches: [ "main" ]`; self_attention.hpp `#define FWD_HW_RESULTS` :19; hunks :660-:685 in `#ifdef FWD_HW_RESULTS` :655-724; `#else` twin :724-851 reads `hw_results_ready[idx]` :730; body names one runtron run; finding 2915270383 at :665.


## Check 4: same experiment run twice

1. `git diff BASE..HEAD -- 't/*' | grep -n '^+.*\(TEST_CASE\|TEMPLATE_TEST_CASE\|SECTION(\|GENERATE(\)'` lists added or widened units. `git log --format='%h %s%n%b' BASE..HEAD -- t/` marks commits answering several gap items at once; their units are the first pair to check.
2. For each unit name the production call under test (the first production call after the unit's own writes). `git grep -n '<call>' HEAD -- t/` lists pre-existing units on the same call; one changed only in API spelling stays out.
3. Follow the call to the leaf function with branches the diff changed. Map every input (each GENERATE value, each token index) to the arm it reaches.
4. Simulate the write order of each unit: a slot counts as observed only if no later write in the same unit replaces it before an assertion reads it.
5. Record per unit the set of (branch, slot, reference, precision, read path) its assertions observe.
6. Compare pairwise. Subset: drop the smaller. Partial: name the (branch, slot) only A observes, give B that observation with one concrete edit, drop A.
7. Compare the comment above each unit with the table: "exercises N cases" holds only if the assertions observe all N.

On PR 4557: units t/t_llama_unit.cpp:3298 (poison GENERATE) and :3650/:3664 (bit-exact section), both `dst_book.append(src_book)` (:3357, :3685), both from commit 707159b9ef. copy_token arms: even<-even andnot v_vnni.hpp:359-364, even<-odd srli :378-384. Poison: dst 2 -> last copy 6<-4 (andnot), dst 3 -> 6<-3 (srli); observed slot 7 via scaled_v at :3385. Bit-exact: page of 64, last copies 63<-61 / 63<-60 overwrite every odd partner before the loop at :3687-3696 reads it; observes copied lanes against source_bits. Verdict: partial overlap; concrete edit = leave the last odd slot of the bit-exact page poisoned, require zero bits after the append, then drop the GENERATE.

Widening (2026-10-06):

## Check 4: same experiment run twice, or run in a new place

1. `BASE=$(git -C WT merge-base HEAD $(gh api repos/positron-ai/tron/pulls/N --jq .base.sha))` (not origin/main; offline: `git -C WT log --first-parent --format='%h %p' origin/main | grep '#N'`, then its first parent).
2. `git -C WT diff BASE..HEAD -- 't/*' | grep -n '^+.*\(TEST_CASE\|TEMPLATE_TEST_CASE\|SECTION(\|GENERATE(\)'`; `git -C WT log --format='%h %s%n%b' BASE..HEAD -- t/`.
3. `git -C WT grep -n '<call>' HEAD -- t/`; compare observed (branch, slot) sets.
4. `git -C WT diff -U0 BASE..HEAD -- 't/*.cpp' | grep -n -E '^\+.*[A-Za-z_]+(->|\.)[a-z_]+\(' | sed -E 's/.*(->|\.)([a-z_]+)\(.*/\2/' | sort | uniq -c | sort -rn`; keep `git -C WT diff BASE..HEAD -- h src | grep -E '^\+.*\b<fn>\('` hits.
5. `git show HEAD:<file> | awk '/^TEST_CASE\(/{name=$0} /<fn>\(/{u[name]++} END{for(k in u) print u[k], k}'`; drop fork-lambda units.
6. `git -C WT grep -n -A4 '<fn>(' HEAD -- h src`; `grep -n 'REQUIRE\|CHECK' full/<file>` inside B's range (locals count).
7. `git -C WT diff --diff-filter=A --name-only BASE HEAD -- 't/'`; `git -C WT diff BASE HEAD -- t/CMakeLists.txt | grep -n -A6 -E '^\+.*(add_catch_test\(NAME <stem>|add_executable_test\()'`; `git -C WT diff BASE HEAD -- config/test-benchmarks.json | grep -n -E '^\+.*"name":"<stem>"'`; `git -C WT grep -n 'slice bench --check$\|slice bench --check ' HEAD -- .github`.
8. `git show HEAD:t/<new>.cpp | grep -n -E 'TEST_CASE|[a-z_]+\('`; `git -C WT grep -n -E '^[A-Za-z_].*\b<fn>\(' HEAD -- h src`; `git -C WT grep -n '<fn>' HEAD -- h src`.
9. `git -C WT grep -n -E 'using [a-z_]+ = <type>' HEAD -- h t`; `git -C WT grep -l -E '<fn>\(|<type><|<alias>' HEAD -- t/ | grep -v <new file>`; `git show HEAD:t/<file> | awk '/^TEST_CASE\(/{name=$0; ln=NR} /<alias> [a-z_]+\(/{print ln": "name" :: "NR": "$0}'`; `git show HEAD:t/CMakeLists.txt | grep -n -A6 'add_catch_test(NAME <existing stem>'`.
10. MODEL_REQUIREMENTS gates (t/CMakeLists.txt:109-150). `grep -n -i '<define>\|run time\|RSS' body.md`; `gh api graphql -f query='{repository(owner:"positron-ai",name:"tron"){pullRequest(number:N){userContentEdits(first:20){nodes{editedAt diff}}}}}'`.

On PR 4265 (HEAD 7a7699b338, BASE a80b102c18): t/t_kv_footprint_memorder.cpp:48 `tron::log_kv_footprint(1, 0)`; t/CMakeLists.txt:843-844 (DEFINES _GLIBCXX_ASSERTIONS); config/test-benchmarks.json:472; h/tron/models/kv_cache.hpp:689 (constructor); t/t_llama_unit.cpp:1704-1706 constructs book_t; t_llama_unit (t/CMakeLists.txt:582-587) lacks only the DEFINES; body cost passage dated 2026-09-10, after 3970127694. Verdict: move.


## Check 5: test name, tags and result print agree with assertions and file convention

BASE = `git -C WT merge-base HEAD origin/$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName)`; if it returns HEAD use `gh api repos/positron-ai/tron/pulls/N/commits --jq '.[0].parents[0].sha'`. Comment anchor: `gh api repos/positron-ai/tron/pulls/comments/<id> -q '.original_commit_id,.original_line'`.

1. `git -C WT diff BASE..HEAD -U0 -- 't/*.cpp' | grep -n '^+++\|^@@\|^[-+]'`; drop re-spelling-only hunks.
2. New units: `git -C WT diff BASE..HEAD -U0 -- 't/*.cpp' | grep -o -E '^\+ *(TEST_CASE_METHOD|TEST_CASE|TEMPLATE_TEST_CASE)\(.*'`; HEAD line: `grep -n -F '<name>' full/<file>`; moved test: `git -C WT show BASE:<file> | grep -c -F '"<name>"'`.
3. Enclosing unit of line L: `git -C WT show HEAD:<file> | awk -v L=<L> '/^(TEST_CASE|TEST_CASE_METHOD|TEMPLATE_TEST_CASE)\(/ {t=NR; name=$0; s=0} /^  SECTION\(/ {s=NR; sn=$0} /^  }$/ {if (s) s=0} NR==L {print (s? s": "sn : t": "name); exit}'`.
4. (A) Comment flips: `git -C WT diff BASE..HEAD -U0 -- <file> | grep -n '^@@\|^[-+] *//'`; new-unit comments: `awk -v S=<S> -v E=<E> 'NR>=S && NR<=E' full/<file> | grep -n '//'`; rename sites: `grep -n '<name>' full/<file>` plus the PR body.
5. (B) Table: `git -C WT show HEAD:<file> | tr '\n' ' ' | grep -o -E '(TEST_CASE_METHOD|TEST_CASE|TEMPLATE_TEST_CASE)\([^{]*\{' | sed 's/ \+/ /g'`; declarations: `grep -n -E '^(TEST_CASE|TEST_CASE_METHOD|TEMPLATE_TEST_CASE)\(' full/<file>`; per-tag members: `... | grep -o -E '"\[[^"]*\]"' | tr -d '"' | sed 's/\]\[/\n/g; s/[][]//g; s/^\.//' | sort | uniq -c | sort -rn`. Convention = shared pre-existing tag count, tags spelled from the name (tag word equals or prefixes a name word).
6. (C) Unit S..E counter prints: `awk -v S=<S> -v E=<E> 'NR>=S && NR<=E' full/<file> | grep -n -A3 -E 'spdlog::(info|warn|error)\(' | grep -B3 -E '(REQUIRE|CHECK)\(.*== *0\)'`; siblings: `git -C WT show HEAD:<file> | grep -n -B1 -E 'spdlog::(info|warn|error)\(".*(found|overall)'`, drop hits whose line above is `++<counter>;`. Guard = `if (` naming the counter.

On PR 4557: BASE e5fa372c19, HEAD 96a6220ab6: SECTION "append_v preserves poison" t/t_llama_unit.cpp:3293 (TEST_CASE :3278), comment flip :3325 "must zero this NaN", REQUIRE_FALSE(std::isnan) :3385 via scaled_v call :3377, header rename site :3273; fixed c5d44bd86f:3275. PR 2078 (B) 9d64b4a8bf: t/t_hwattention.cpp:1787 `[hwattention][pos]` fires, :1869 `[dma_xfer_state]` does not. PR 1666 (C) b0e53be7e0: t/t_hwattention.cpp:1376 unguarded, siblings :567, :597, :714, :744 guarded.


## Check 33: a changed path needs a test through its production entry

HEAD = review record commit. BASE = merge base on the PR base branch:
```
B=$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName)
BASE=$(git -C WT merge-base HEAD origin/$B) # merged: HEAD <mergeCommit>^1
```
1. `git -C WT diff --diff-filter=A --name-only BASE HEAD -- 'h/*' 'src/*'`; per header `git -C WT show HEAD:<hdr> | grep -n -E '^ *(class|struct) [A-Za-z_]+|Note \[|\b(must|exactly once|wrap|full|empty)\b'`; `git -C WT grep -l -w <name> HEAD -- t/` empty = finding.
2. `git -C WT diff -U0 BASE HEAD -- 'h/*' 'src/*' | grep -E '^\+[ \t]*(template *<[^>]*> *)?([A-Za-z_][A-Za-z_0-9:<>,*& ]* +)?[~A-Za-z_][A-Za-z_0-9:]*\([^;]*\)[ \t]*(const)?[ \t]*(noexcept)?[ \t]*\{[ \t]*$' | grep -v -E '^\+[ \t]*(if|for|while|switch|return|else|TRON_|REQUIRE|CHECK|static_assert|catch)\b'`; hunk starts `awk '/^\+\+\+ b\//{f=substr($0,7)} /^@@/{split($3,a,/[+,]/); print f, a[2]}'`; enclosing definition `git -C WT show HEAD:<file> | awk -v L=<line> 'NR<=L && /^[ \t]*([A-Za-z_][A-Za-z_0-9:<>,*& ]* +)?[~A-Za-z_][A-Za-z_0-9:]*\([^;]*(\)[ \t]*(const)?[ \t]*(noexcept)?[ \t]*\{[ \t]*$|,$)/ && !/^[ \t]*(if|for|while|switch|return|else|TRON_|REQUIRE|CHECK|static_assert|catch|TRACE)/ {name=$0} END{print name}'`.
3. Per F: `git -C WT grep -n -w F HEAD -- t/` and `-- h/ src/`; callers up three levels; callees down to the first t/ hit. Branch: `git -C WT diff -U0 BASE HEAD -- <file> | grep -E '^[-+].*\b(if|for|while|switch)\b|\?|\.(size|empty)\(\)'`. TEST_CASE: `git -C WT show HEAD:<test> | awk -v L=<line> 'NR<=L && /TEST_CASE\(/ {name=$0; n=NR} END{print n": "name}'`.
4. `git -C WT diff -U0 BASE HEAD -- 'h/*' 'src/*' | grep -n -E '^[-+][^/]*\b[A-Za-z_]+(\.|->)[A-Za-z_.]+ *= *[^;=]*[%*/+-]' | grep -v -E '= *[^;]*->'`; `git -C WT grep -n -E '(\.|->)<field> *=' HEAD -- t/`; substitute `grep -n '<local> ='`.
5. `git -C WT diff -U0 BASE HEAD -- 't/*' | grep -n -B2 -A2 -E '^-.*(::acquire\(|pos_allocate|std::make_shared<)|^\+.*= *(dev|device)->[a-z_]+;'`; pair by variable; `git -C WT grep -n '<new>' HEAD -- h/ src/`.

On PR 4128 (97de6ee02c, BASE 130ad3a652): h/tron/self_attention.hpp:793 -> help_drain_gof (h/tron/models/model.hpp:2988, 0 t/ hits, loop :3003) -> fire_gof_rodeo_batch (:3039) -> gof_rodeo_impl_batch (:3063) -> src/tron/gof.cpp:455 -> shard::xfer_gofs at t/t_phase1_integration.cpp:910; 3960538961 :3005. PR 2903 (64ea13a671): h/pos/minfifo.hpp:8 Note, 0 t/ hits. PR 1997 (c502e4d61a): src/pos/worker.cpp:925 vs t/t_hwattention_replay.cpp:549. PR 1920 (2d53016b44): t/t_hwattention.cpp:169.


## Check 34: a workaround for an unexplained defect needs a tracked exit

1. `BASEREF=$(gh pr view N --json baseRefName -q .baseRefName); BASE=$(git -C WT merge-base HEAD origin/$BASEREF); gh pr view N --json body -q .body > body.md`
2. `git -C WT diff -U0 BASE HEAD -- h src t | awk '/^\+\+\+ /{f=substr($2,3)} /^@@/{split($3,a,/[,+]/); n=a[2]; next} /^\+/{print f":"n": "$0; n++}' | grep -i -E 'work-?around|\bhack\b|unidentified|unexplained|not understood|root cause|open question'`
3. `git -C WT log --format='COMMIT %h %s%n%b' --no-merges BASE..HEAD | awk '/^COMMIT /{c=$2} /work-?around|unexplained|root cause|open question|no longer (necessary|needed) (with|in|on|since) |fixed in (bitfile|firmware|release|v?[0-9]+\.[0-9]+)/ {print c": "$0}'`; keep a commit only if `gh api repos/positron-ai/tron/commits/<sha>/pulls --jq '.[].number'` lists N.
4. `grep -n -i -E 'work-?around|pending (a |the )?(fix|bitfile|firmware)|until (we|a|the) .*(bitfile|firmware|fix)|bitfile [0-9]' body.md`
5. Unknown-cause hit counts only with: `git -C WT show HEAD:FILE | sed -n "$((L-15)),$((L+15))p" | grep -i -E 'work-?around|\bhack\b'`. UNEXPLAINED -> 6; obsolescence commits -> 8.
6. Same window `| grep -n -E 'STORY-[0-9]+|[A-Za-z_]+#[0-9]+|#[0-9]{3,}|notion\.so/|/issues/[0-9]+'`; `git -C WT log --format='%h %s' -S'<phrase>' BASE..HEAD` (oldest), `git -C WT log -1 --format=%B <sha> | grep -n -E '<id pattern>'`; a body.md id counts only in a step-4 paragraph.
7. `git -C WT grep -n -i -E 'work-?around|silently flipped|\bhang\b|required for production' HEAD -- $(git -C WT diff --name-only BASE HEAD -- 't/*')`; `git -C WT show HEAD:<test> | awk -v L=<line> 'NR<=L && /TEST_CASE\(|SECTION\(|TEMPLATE_TEST_CASE\(/ {n=NR; name=$0} END{print n": "name}'`; `git -C WT show HEAD:<test> | awk -v S=<start> 'NR>=S {print NR": "$0} NR>S && /REQUIRE|CHECK/ {exit}'`; needs a consumer sentence or `grep -c -E 'TODO'` > 0.
8. `git -C WT show <sha> | grep -o -E '^-[^/]*\b[a-z_]*(clear|zero|scrub|nan)[a-z_]*\b' | sort -u`; `git -C WT grep -n -i -E '<stems>|clear_|zero_|zeroi[sz]e|scrub' HEAD -- h src t`; `git -C WT grep -n -E 'TRON_[A-Z_]*WORKAROUND' HEAD -- h src t CMakeLists.txt t/CMakeLists.txt nix flake.nix CMakePresets.json GNUmakefile`.

On PR 2713 (head 25d146aa15, BASE 4bc2416b05, origin/hwattention_sync): step 2 src/system/heap_v2.cpp:293, :302, t/t_heap_v2.cpp:226, :230; step 3 32e7c3d6be; step 6 0 ids -> 3227447122; step 7 t/t_heap_v2.cpp:224, header :226-231, no TODO -> 3227468540. PR 2176 (head 9553cd0a11): step 3 d3e1020563; step 8 clear_kv_hbm t/t_hwattention.cpp:63, no gate -> 2948238427.


## Check 6: guarantee claim versus enforcing declaration

1. Extract claims: `grep -n -i -E 'compile error|cannot be (passed|handed)|reject|enforce|no (bare|raw|public) pointer|STATIC_REQUIRE|static_assert|typed view so that|neither takes' body.md pr.diff`. For each hit write (subject set, forbidden input, claimed mechanism). Expand plurals.
2. For each subject, find every parameter in the diff's added lines whose type names the subject; resolve the type through every `using` (`git show HEAD:<file>`) to its struct or class definition. Record: new class, or alias of a generic template.
3. Levels. (1) `explicit` on the pointer constructor of the resolved type. (2) Public pointer constructor present at all: `grep -n -E 'explicit|constexpr (view|const_view)\(' <definition file>`; a wrap in one expression at any call site shows the route is open: `git grep -n -E '<Alias><[^>]*>\{' HEAD -- h src t`. (3) `using` alias of a generic template: cite the alias and one other producer of the same instantiation.
4. Opposite-direction assertions: `grep -n 'is_constructible_v\|is_same_v' full/<test>` around the cited probes.
5. Design record, when present: `grep -n -i -E 'still permits|remains legal|does not prove|limitation|not a .* guarantee' <design file>`; quote any limitation the claim drops.
6. Truth table per subject with the deciding file:line for each level. The sentence holds only if every subject reads rejected at every level it implies, or the text names the open levels.
7. One finding per failing subject, anchored at the alias definition; the body row, header comment and test comment are citations, not findings.

On PR 4557: body row 65 (subjects packed V, native K); kernel parameter const_native_k_view at h/tron/kernels/amx_attn_iface.hpp:222; alias kv_cache_fwd.hpp:49-53 of const_view (view.hpp:296, `explicit`); level 1 rejected for K and V (t_llama_unit.cpp:383); level 2 open for K (:397, wrap at t_amx_numerics.cpp:165), closed for V (v_vnni.hpp:130-138 private); level 3 open for K (alias), closed for V (new class); design record round 4 row 280 "still permits an explicit ordinary pointer wrap". The limitation at t_llama_unit.cpp:392-393 clears the probes' own comment block :371-373, not the body row.

Widening (2026-10-06):

## Check 6: claim wider than the code (guarantees, timed paths, element counts, defaults)

0. BASE = `git -C WT merge-base HEAD origin/$(gh pr view N --json baseRefName -q .baseRefName)`; merged: M = `git -C WT log --merges --first-parent --format=%H --grep='#N' origin/<base>`, BASE = `git -C WT merge-base HEAD M^1`.
1. (a) prose only: `grep -n -i -E 'compile error|cannot be (passed|handed)|reject|enforce|no (bare|raw|public) pointer|STATIC_REQUIRE|static_assert|typed view so that|neither takes' body.md log.txt`; same over `grep -n -E '^\+\s*(//|\*)' pr.diff` and `git -C WT diff BASE HEAD -- doc 'README*.md'`.
2. (b): `git -C WT diff BASE HEAD -- h src t | grep -n -E '^\+.*(rdtsc\(\)|inc_relaxed\(|fetch_add\(|_cycles\b|note_[a-z_]+\()'`. L of X: `grep -n -o -E 'T[0-9] = .*' body.md`; `git -C WT show HEAD:<hdr> | grep -n -o -E 'T[0-9] = [^.]*'`. `grep -n -E "X|\bL\b" body.md`; `for f in <doc+diff files>; do git -C WT show HEAD:$f | tr '\n' ' ' | grep -o -E "[^.]*(X|\bL\b)[^.]*\."; done | grep -w -i -E 'ends when|whichever|in both|either|every'`.
3. (b): `git -C WT show HEAD:<file> | grep -n -E 'const bool (join_hw|uses_hw)|if \((!)?(join_hw|uses_hw)|hw_plan\.empty|continue;  // poll|while \(!'`; stamps: `... grep -n -E 'X|t_wait|t_poll|rdtsc'`; fn of stamp S: `awk 'NR<=S && /^    [a-z_:<>]+ [a-z_]+\(/ {l=NR": "$0} END{print l}'`; guard branch = path.
4. (b) body at review: `gh api graphql -f query='query{repository(owner:"positron-ai",name:"tron"){pullRequest(number:N){userContentEdits(first:30){nodes{editedAt diff}}}}}'` (last edit before it); `grep -n -E '"X":0' body.md README*.md`; sibling: `git -C WT grep -n 'note_fpga_pass(' HEAD -- h src`.
5. (c): `git -C WT diff BASE HEAD -- h src | grep -n -E '^\+.*(\[0\]|\.front\(\))'`; C: `git -C WT grep -n -i -E 'one or more|multiple|several|a list of|exactly one|at most one' HEAD -- doc 'README*.md' h src | grep -i 'C'`; `git -C WT grep -n -E 'C\.(push_back|emplace_back|insert|resize)\(' HEAD -- h src`; F: `git -C WT grep -n -E '\bF\(' HEAD -- h src t`.
6. (d): `grep -n -E 'option\(|default (ON|OFF)|getenv' pr.diff`; `git -C WT grep -n -E "S" HEAD -- '*CMakeLists.txt' h src doc 'README*.md'`; `git -C WT grep -n -E "compile_definitions\(.*S" HEAD`; `#define S 0` under `if(S)`: ask only.

On PR 4596 (5342222359 at 1430736b2a, BASE 66c7bb8db1): `join_wait_cycles` self_attention.hpp:1027/:1188 = T5; README.stats.md:260-262 2 paths; `join_hw` :1251; hw start :1132, stop :1147 under `if (join_hw)` :1300; sw poll :1258 untimed; body:94 `"join_wait_cycles":0,"fpga_k_tokens":0`, note_fpga_pass only :636 = 4125033634.


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

Widening (2026-10-06):

## Check 8: body and branch match the reviewed head

Setup:
```
read BASEREF BASEOID HEADOID < <(gh pr view N --repo positron-ai/tron --json baseRefName,baseRefOid,headRefOid -q '[.baseRefName,.baseRefOid,.headRefOid]|@tsv')
BASE=$(git -C WT merge-base $HEAD $BASEOID)
```
1. `grep -oE '\b[0-9a-f]{7,40}\b' body.md | grep -E '[a-f]' | sort -u` in results sections, outside code and JSON.
2. `git -C WT cat-file -t ID; git -C WT merge-base --is-ancestor ID $HEAD; gh api repos/positron-ai/tron/commits/ID --jq .sha` (404/422 = twin).
3. `for f in $(cat prfiles.txt); do git -C WT diff --quiet ID $HEAD -- $f || echo $f; done`
4. `gh api graphql -f query='{repository(owner:"positron-ai",name:"tron"){pullRequest(number:N){createdAt lastEditedAt userContentEdits(first:50){nodes{editedAt diff}}}}}'` (`diff` = full body).
5. `git -C WT log --no-merges --author='<author>' --format='%h %cI %s' --since=LAST $BASE..$HEAD`
6. `grep -nE '[0-9]+ (cases|tests|assertions)|keyed by|per (pool |attention )?(worker|layer|forward)|owns|T[1-9] =' body.md | grep -v '^[0-9]*:[ ]*[\[{"]'`; keep only if `git -C WT log --format=%h -S'<identifier>' --since=LAST $BASE..$HEAD` is non-empty; `git -C WT grep -n '<subject identifier>' $HEAD -- h src t`; `git -C WT show $HEAD:<test> | grep -c '^TEST_CASE'`
7. `gh pr view N --json mergeable,mergeStateStatus`; posted review or merged PR: `git -C WT merge-tree $BASE $HEAD $BASEOID > mt.txt; grep -c '<<<<<<<' mt.txt`.
8. `grep -nEiw 'ported|copied|extracted|cherry-pick|cherry-picked|originally authored' body.md`; `git -C WT log -1 --before='<review time>' --format='%h %cI %s' origin/S -- <path>`; `git -C WT show <id>:<path>` or `gh api "repos/positron-ai/tron/contents/<path>?ref=<id>" --jq .content | base64 -d`; `diff <(git -C WT show <source>:<path>) <prcopy> | grep '^>' | grep -oE '\b[a-z_]+\(' | tr -d '(' | sort -u`; per symbol `git -C WT log -1 --before='<review time>' --format="$s %h %s" -S"$s" origin/S -- <path>`.
9. `gh api repos/positron-ai/tron/pulls/N/comments --paginate --jq '.[] | select(.body | test("```suggestion")) | [.id,.user.login,.path,.original_commit_id[0:10],.original_line] | @tsv'`; `git -C WT show <orig>:<path> | sed -n '<original_line>p'`; grep that text in `git -C WT show $HEAD:<path>`.

On PR 4596 (head 441e81178b, BASE 66c7bb8db1): stale "per attention worker" (pool_worker at h/tron/models/attn_stats.hpp:431, bff317e0d3), "12 cases" (17 TEST_CASE in t/t_attn_stats.cpp); merge-tree 1 block in h/tron/models/model.hpp; PR 2676: 36cf204564:h/tron/gof.hpp:151-182 keeps six gof_* symbols a02939c11a removed.


## Check 9: PR-body passages a GitHub reader cannot use

1. Section ranges as in check 8.
2. `grep -n -E '[0-9]{2}:[0-9]{2}(:[0-9]{2})? ?(UTC|Z)|/var/tmp/|/tmp/|/home/|[A-Za-z0-9_.-]+\.log\b|[0-9]+ [+-] [0-9]+ = [0-9]+|= [0-9]+ matches|(fewer|more) assertions than' body.md` within the ranges. No marker for `rc`; rc clauses are the keep anchor.
3. Dangling ids that label a result go to check 8. Ids in the commit table or the review-outcome table are not findings.
4. Reader test per hit; bins: clock times (keep the date), machine paths and log names (delete), reconciliations against an earlier revision (delete).
5. Report once per section, phrased as an ask.

On PR 4557: body:158 (four UTC build windows, /var/tmp log path), :160 (19:51 to 19:56 UTC), :162 (8196 = 4 + 8192 against c73e7fb2f9).

Widening (2026-10-06):

## Check 9: Passages a later reader cannot use: PR-body sections, code comments and Notes
BASE = merge base of HEAD and `gh api repos/positron-ai/tron/pulls/N --jq .base.sha` (the PR's base branch, not origin/main); 0 merges in BASE..HEAD.
6. Review labels (R), tracker ids (T, h/ src/); adjacent lines = 1 comment:
```
PATR='(PR ?#?[0-9]{3,5}[ ,]+(review|round|comment)|review round|round [0-9]|comment [WR][0-9]|R[0-9]+-M[0-9]+|as discussed with)'
PATT='([Ss][Tt][Oo][Rr][Yy][ -]?#?[0-9]+|[Tt]icket[ -]?#?[A-Z]*-?[0-9]+|JIRA|issue #[0-9]+)'
git -C WT diff -U0 BASE HEAD -- h src t | grep -E '^\+\+\+|^@@|^\+' | awk -v pr="$PATR" -v pt="$PATT" '/^\+\+\+/{f=substr($0,7)} /^@@/{split($0,a," "); split(a[3],b,","); n=substr(b[1],2)+0; next} /^\+/{ if ($0 ~ /^\+[ \t]*(\/\/|\*|\/\*)/) { if ($0 ~ pr) print "R " f":"n": "substr($0,2); else if ($0 ~ pt) print "T " f":"n": "substr($0,2) } n++}'
```
7. New Notes; outside cites; story words below the tilde line + body overlap = history:
```
git -C WT diff -U0 BASE HEAD -- h src t | grep -E '^\+\+\+|^@@|^\+' | awk '/^\+\+\+/{f=substr($0,7); p=""} /^@@/{split($0,a," "); split(a[3],b,","); n=substr(b[1],2)+0; p=""; next} /^\+/{ line=substr($0,2); if (p ~ /^[ \t]*\/\/ Note \[/ && line ~ /^[ \t]*\/\/ ~~~~/) print f":"n-1": "p; p=line; n++}'
git -C WT grep -n 'Note \[NAME\]' HEAD -- h src t | grep -v FILE
git -C WT show HEAD:FILE | sed -n 'L+2,ENDp' | grep -n -E '\bNaN\b|\bcrash\b|\babort\b|\bwrong\b|\bbug\b|\bthe fix\b|\bused to\b|\bno longer\b|\bthe latter put\b|qwen|llama|gpt|mixtral|bitfile'
gh pr view N --repo positron-ai/tron --json body -q .body | grep -c -F 'MARKER'
```
8. Feature-link comment (FEATURE = Note names | title identifiers); all TOKENs at BASE = drop the comment, once per PR:
```
git -C WT diff -U0 BASE HEAD -- h src t | grep -E '^\+\+\+|^@@|^\+' | awk -v feat="FEATURE" '/^\+\+\+/{f=substr($0,7); c=""; k=0} /^@@/{split($0,a," "); split(a[3],b,","); n=substr(b[1],2)+0; c=""; k=0; next} /^\+/{ line=substr($0,2); if (line ~ /^[ \t]*\/\//) {c=c "\n" line; k++} else { if (k>=1 && k<=3 && line ~ /(TRACE_EVENT|TRACE_COUNTER|spdlog::|TRON_ASSERT|LOG\(|->inc|fetch_add)/ && c ~ ("See Note \\[|" feat)) print f":"n": lines=" k ": " line c; c=""; k=0 } n++}'
git -C WT grep -c 'TOKEN' BASE -- h src t
```
9. Final head: step 6 empty; `git -C WT grep -c 'Note \[REMOVED\]' HEAD -- h src t` = 0.
On PR 4596 at 0f784c44ff (BASE 66c7bb8db1): step 6 attn_stats.hpp:863-864 (4146947611), t/t_attn_stats.cpp:306 (4146959502), t/t_llama_unit.cpp:2227; step 7 attn_stats.hpp:6 Note [Attention path stats] kept; step 9 at 441e81178b: 0.


## Check 10: hunk-to-claim trace

1. Identifier set: backticked names and Note titles in "What changes" + names declared at namespace or class scope in `git diff BASE..HEAD --diff-filter=A --name-only` files, minus names with `git grep -c NAME BASE` > 0. Write the list with its `grep -c` count over pr.diff.
2. Bin commits from log.txt (SIDE / MAIN-FEATURE as in SKILL.md). Scan every non-merge commit, SIDE first: `git show <sha> -- FILE` per file.
3. Candidate hunk test: at least half of its `-` lines in `git show BASE:FILE` verbatim, at least one not blank, brace-only or comment-only, no identifier in the `+` lines. Inheritance within the same function or TEST_CASE.
4. Clearance: rename-map identity; a GitHub review thread id; a body sentence describing the added content. A sentence naming only the file or callee does not clear; a contradicting sentence is quoted.
5. Test hunks: callee untouched by the PR -> unrelated; callee rewritten -> regression guard, body gap at most.
6. Revert test (both): the hunk changes lines that exist at BASE; reverting it alone keeps every body sentence true, every identifier compiling, and every assertion passing at HEAD also passing at BASE. If the hunk is the sole test of a PR symbol's forwarded behavior, report a body gap and let the author choose.
7. One finding per hunk.

On PR 4557: ec795fbce8 (src/tron/kernels/amx_attn.cpp:152-181, 35 of 36 removed lines at BASE, 0 identifiers, body:52 "The tile loads are unchanged" contradicts) -> unrelated, split out. 39a6899446 carries t/t_heap_v2.cpp:1209-1223 (CHECK is_aligned, contract alloc_align at BASE memory.hpp:146); it is the only test of the new operator new[]'s alignment forwarding -> body gap, author's choice. 959d1ae229 partner-zero rows: callee append_v_row rewritten by the PR -> regression guard, not unrelated.

Widening (2026-10-06):

## Check 10: hunk-to-claim trace (unrelated, unexplained or merge-dropped changes)

Setup (G: shorthand):
```
G="git -C WT"; BR=$(gh pr view N --repo positron-ai/tron --json baseRefName -q .baseRefName); BASE=$($G merge-base HEAD origin/$BR)
# merged PR: M=$(gh api repos/positron-ai/tron/pulls/N --jq .merge_commit_sha); BASE=$($G merge-base $M^1 HEAD)
```
1. Identifiers: body backticks in pr.diff; created files: `$G show HEAD:FILE | grep -E '^(struct|class|static|constexpr|inline|using|TEST_CASE)'`.
2. Candidate hunk: half its `-` lines in `$G show BASE:FILE`, one substantive, no identifier added.
3. FILE: `$G diff --name-status BASE..HEAD | grep -E '^(A|D|R)'`; `STEM=$(basename P | sed 's/\..*//')`; `grep -i -w -c -F "$STEM" body.md log.txt`, also with `_`/`-` as space and `grep -i -c -F "$(dirname P)/"`; 0 hits on D/R = candidate; `$G log --diff-filter=AD --format='%h %s' BASE..HEAD -- P`.
4. COMMENT: `$G diff -U0 BASE..HEAD | grep -n -E '^-\s*(//|\*|#)' | grep -i -E 'DO NOT RENAME|DO NOT REMOVE|packag|parsed by|read by|regex|grep|cmake|script|depend'`; adder `$G log --format='%h %ci %s' -S'TEXT' origin/main -- FILE | tail -1`; consumer `$G grep -n 'STEM' REV -- ':!h' ':!src'` at BASE and origin/main; remover `$G log -m --format='%h %p %s' -S'TEXT' HEAD -- FILE`.
5. MERGE: (a) merge PRs: `SRC=$($G rev-list -1 --first-parent --before='TIME' origin/BRANCH)`; per `+` line of `$G diff -U0 BASE..HEAD`: `$G grep -q -F -- 'LINE' $SRC -- FILE`; absent in all = candidate. (b) per M in `$G log --merges --format=%h BASE..HEAD`: `$G diff -U0 M^2 M`; keep `-`-only hunks whose line `$G grep -F 'LINE' M -- h src t CMakeLists.txt cmake` finds nowhere and is at M^1 or absent at `$G merge-base M^1 M^2`; clear if HEAD re-comments it or its symbol is gone.
6. FLAG: `$G diff BASE..HEAD -- '*CMakeLists.txt' '*.cmake' | grep -n -E '^\+.*(target_compile_options|target_compile_definitions|add_compile_definitions|(^|[:;" ])-m[a-z0-9]+)'`; siblings `$G grep -n -E 'mavx512|mavx2|mfma|TRON_AVX512_ENABLED' HEAD -- '*CMakeLists.txt'`.
7. Clear: rename map; thread id; body or subject naming the item; consumer at the adder, gone at HEAD. Body edit times: `gh api graphql` on `pullRequest(number:N){userContentEdits(first:20){nodes{editedAt}}}`.

On PR 3738: HEAD 819d4c96b8, BASE c0251042c5; step 4: h/pos/config.hpp:104-106 ("DO NOT RENAME as packaging is dependent on finding these values"); `min_bitfile` 0 hits at BASE, CMakeLists.txt:820 at origin/main (after the review); adder 642f443046, remover merge b815ae9ad4; step 5b keeps `@@ -104,3`, clears `@@ -69,2`; constants at HEAD:96-98.


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


## Check 35: a bot finding is traced to the deciding line

Setup: `BASEREF=$(gh pr view N --json baseRefName -q .baseRefName); BASE=$(git -C WT merge-base HEAD origin/$BASEREF)`.

1. `gh api graphql -f query='query($n:Int!){repository(owner:"positron-ai",name:"tron"){pullRequest(number:$n){reviewThreads(first:60){nodes{isResolved isOutdated comments(first:3){nodes{databaseId path line author{login}}}}}}}}' -F n=N > threads.json`; keep first author `cursor`, both flags false, one comment node.
2. `gh api repos/positron-ai/tron/pulls/N/comments --paginate --jq '.[] | select(.user.login | endswith("[bot]")) | [.id, .path, .line, .commit_id[0:10], (.body | capture("\\*\\*(?<s>[A-Za-z]+) Severity\\*\\*").s), (.body | split("<!-- DESCRIPTION START -->")[1] | split("<!-- DESCRIPTION END -->")[0] | gsub("\n";" "))] | @tsv'`; `git -C WT diff -U0 BASE HEAD -- <path> | grep -n '^@@'`.
3. SENTINEL: `git -C WT show HEAD:<file> | sed -n '<line-5>,<line+2>p'`; `git -C WT show HEAD:<file> | grep -n '<object>\b'`; `git -C WT grep -n -E '<member>\(|with_<member>\(' HEAD -- h src | grep -E 'cfg->|with_<member>|<ObjectType>'`; `git -C WT grep -n -E ', <Type>\(|<Type>_t [a-z_]+\(|\b<Type>\(\*' HEAD -- h src t`.
4. UNREACHABLE: `git -C WT show HEAD:<gate file> | cat -n`; `gh pr view N --repo positron-ai/tron --json title -q .title`; `grep -n -i '<behavior words>' body.md`.
5. UNUSED: `git -C WT grep -n '<symbol>(' HEAD -- h src t ingest`; `git -C WT grep -n -E '#include.*<file>' HEAD -- h src t`; `git -C WT show HEAD:<file> | grep -n '<symbol>'`. CONCURRENCY: `git -C WT grep -n -i -E '<container>.*(lock|mutex|append-only|only grows|never removed|single writer)' HEAD -- h src`; invariant REFUTED, hazard note CONFIRMED, else UNKNOWN.
6. Record a verdict per live finding; post only with the deciding line quoted; UNKNOWN only with a named run.
7. Agent review: `git -C WT grep -n '#undef\|<upstream macro prefix>' HEAD -- <copying header>`; `git -C WT grep -n -E '#include *<<upstream>' HEAD -- h src | grep -v <gating header>`; `grep -n -i 'single.writer\|one writer' <header>`. Forward kept items quoted, optional.

On PR 2426 (head 4666560ff1, base 1a88e897e1): 3075799768 SENTINEL h/tron/models/model.hpp:829; initializer h/tron/scheduler/full.hpp:1060-1062; callers full.hpp:1063, t/t_llama_unit.cpp:296, src/tron/gof_model.cpp:12-13; REFUTED. 3075799795 UNUSED h/tron/gof.hpp:89; callers model.hpp:1598, t/t_phase1_integration.cpp:835; REFUTED. 3075799778 CONCURRENCY full.hpp:962-966; UNKNOWN. PR 3488 (2a3fb52d5a): 3659990818 src/tron/models/hw_attn_config.cpp:16; INTENDED.
