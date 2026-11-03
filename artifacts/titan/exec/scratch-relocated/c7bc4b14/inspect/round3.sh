#!/bin/bash
export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0 PAGER=cat
T() { timeout 20 "$@" 2>&1; }
sec() { printf '\n=== %s ===\n' "$1"; }
sec date; date -u

sec authorized_key_fingerprints
ssh-keygen -lf ~/.ssh/authorized_keys 2>&1; echo "--- raw line lengths"; awk '{print NR": len="length($0)" fields="NF}' ~/.ssh/authorized_keys

sec toolchain_readme
stat -c 'README mtime=%y' ~/positron/tools/README-toolchain.md; echo "----- README-toolchain.md (first 80 lines)"; head -80 ~/positron/tools/README-toolchain.md 2>&1; echo "----- sdk-toolchain.sh (first 60 lines)"; head -60 ~/positron/tools/sdk-toolchain.sh 2>&1
echo "--- toolchain env binaries"; E=~/positron/toolchains/sdk-ci-2026-10; ls $E/bin 2>&1 | grep -E '^(clang|clang\+\+|clang-18|ninja|cmake|python3?|python3\.[0-9]+|lld|ld\.lld|llvm-config|gcc|g\+\+)$' | tr '\n' ' '; echo; echo "clang: $($E/bin/clang --version 2>&1 | head -1)"; echo "ninja: $($E/bin/ninja --version 2>&1)"; echo "cmake: $($E/bin/cmake --version 2>&1 | head -1)"; echo "python: $($E/bin/python --version 2>&1)"; echo "python3 -c sysconfig: $($E/bin/python -c 'import sysconfig;print(sysconfig.get_config_var("INCLUDEPY"))' 2>&1)"
echo "--- micromamba"; ls -la ~/positron/tools/micromamba 2>&1 | head; ~/positron/tools/micromamba/bin/micromamba --version 2>&1 | head -1; ~/positron/tools/micromamba/micromamba --version 2>&1 | head -1

sec runs_and_checks
echo "--- runs/"; ls -la ~/positron/runs; for d in ~/positron/runs/*/; do echo "## $d"; ls -la "$d" | head -15; done
echo "--- ev2-build-job.sh (head 40)"; head -40 ~/positron/runs/ev2-build-job.sh; echo "--- ev3-churn-job.sh (head 40)"; head -40 ~/positron/runs/ev3-churn-job.sh
echo "--- check/r1"; ls -la ~/positron/check/r1 | head -30; echo "--- latency.rejudge.json (head 1500 bytes)"; head -c 1500 ~/positron/check/r1/latency.rejudge.json 2>&1; echo; echo "--- r1-run.rec_bind.check.txt (head 30)"; head -30 ~/positron/check/r1/r1-run.rec_bind.check.txt 2>&1
echo "--- hiccup run contents"; find ~/positron/runs/hiccup -maxdepth 2 | head -30; for f in $(find ~/positron/runs/hiccup -maxdepth 2 -type f \( -name '*.json' -o -name '*.txt' -o -name '*.log' -o -name '*.md' \) | head -4); do echo "## $f"; head -c 1200 "$f"; echo; done
echo "--- logits-bench contents"; find ~/positron/runs/logits-bench -maxdepth 2 | head -20
echo "--- churn-r1 contents"; find ~/positron/runs/churn-r1 -maxdepth 2 | head -20

sec src_work_venvs
echo "--- src/phoenix-int"; ls -la ~/positron/src/phoenix-int | head -30; for f in ~/positron/src/phoenix-int/README* ~/positron/src/phoenix-int/*.md; do [ -f "$f" ] && { echo "## $f"; head -40 "$f"; }; done; echo "git: $(git -C ~/positron/src/phoenix-int remote -v 2>&1 | head -2 | tr '\n' ' ') @ $(git -C ~/positron/src/phoenix-int log -1 --format='%h %cd %s' --date=iso 2>&1)"
echo "--- work/"; for d in ~/positron/work/*/; do echo "## $d"; ls -la "$d" | head -12; done; for f in $(find ~/positron/work -maxdepth 2 -type f \( -name '*.md' -o -name '*.txt' -o -name '*.log' \) | head -6); do echo "## $f"; head -25 "$f"; done
echo "--- venvs"; for v in ~/positron/venvs/*/; do echo "$v: $($v/bin/python --version 2>&1) packages=$($v/bin/pip list 2>/dev/null | wc -l)"; $v/bin/pip list 2>/dev/null | grep -iE 'positron|sdk|phoenix|torch|numpy|nanobind' | head -8; done
echo "--- weights"; ls -la ~/positron/weights/qwen3_5_0_8b | head; echo "--- deps"; ls ~/positron/deps; echo "--- pyinc"; ls ~/positron/pyinc/python3.12 | head -5
echo "--- authorship hints (grep in scripts/docs)"; grep -rIiE -m2 'jeremy|sw-dev-01|jhan|jibin|claude|author|generated' ~/positron/tools ~/positron/runs/*.sh ~/positron/work --include='*.md' --include='*.sh' --include='*.txt' 2>/dev/null | head -20

sec user_journal
T journalctl --user --no-pager -o short-iso 2>&1 | grep -vE 'Hint:|Users in groups|Pass -q' | head -40

sec residual_tick_under_load
echo "arch_timer (IRQ 12) count on CPU 121: idle 5 s, then busy 5 s (pinned spin), from /proc/interrupts"
col() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1=="12:"{print $(k+1)} ' /proc/interrupts; }
ipi() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1 ~ /^IPI/ {s+=$(k+1)} END{print s}' /proc/interrupts; }
allirq() { awk -v c="CPU$1" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} {s+=$(k+1)} END{print s}' /proc/interrupts; }
a=$(col 121); ai=$(ipi 121); aa=$(allirq 121); sleep 5; b=$(col 121); bi=$(ipi 121); ba=$(allirq 121)
echo "idle 5 s: arch_timer=$((b-a)) IPIs=$((bi-ai)) all_irqs=$((ba-aa))"
a=$(col 121); ai=$(ipi 121); aa=$(allirq 121); taskset -c 121 timeout 5 bash -c 'while :; do :; done'; b=$(col 121); bi=$(ipi 121); ba=$(allirq 121)
echo "busy 5 s: arch_timer=$((b-a)) IPIs=$((bi-ai)) all_irqs=$((ba-aa))  (HZ=250 would give 1250 ticks in 5 s)"
echo "--- same for CPU 125 busy 5 s"; a=$(col 125); aa=$(allirq 125); taskset -c 125 timeout 5 bash -c 'while :; do :; done'; b=$(col 125); ba=$(allirq 125); echo "busy 5 s cpu125: arch_timer=$((b-a)) all_irqs=$((ba-aa))"
echo "--- context switches on cpu121 during busy 5 s (from /proc/schedstat if readable)"; head -c 200 /proc/schedstat 2>&1 | head -3

sec end; date -u; echo DONE
