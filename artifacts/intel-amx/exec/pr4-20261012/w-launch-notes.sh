#!/usr/bin/env bash
# Not a script to run blindly: the commands of campaign W's launch (PR4-handoff.md section 5.3, the fork's README), in order.
# 1. After the chain's step deb (run 1), read the base manifest on 3bda:
#      ssh delphi-3bda 'python3 -c "import json; m=json.load(open(\"/var/tmp/jhan/pr4ci-20261012/manifest-base.json\")); print(m[\"version\"], m[\"rinzler_sha256\"])"'
# 2. The check mode (read-only against the DUT; the lease must be free and serving up; run it before run 2 takes serving down):
#      H=~/workspace/intel-AMX/exec/pr4ci-20261012; RESD=~/workspace/intel-AMX/exec/results/pr4ci-20261012; ST=~/workspace/ai-runs/systems_test; mkdir -p $RESD/check-mode; (cd $ST && env PYTHONPATH="$H/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CI_MIMIC_CHECK=1 CI_MIMIC_ARM=check-mode CI_MIMIC_OUT=$RESD/check-mode/perf.json TALOS_STUB_OUT=$RESD/check-mode/talos.json CI_MIMIC_MODELS= CI_MIMIC_CONFIGS_JSON= CI_MIMIC_AMX_PROBE=0 CI_MIMIC_REQUIRE_HWATTN0=0 CI_MIMIC_REQUIRE_HWATTN_UNSET=0 CI_MIMIC_LEASE_CHECK=1 CI_MIMIC_DUT_HELPER=$H/dut.sh $ST/.venv/bin/python $H/st_ci_perf.py >$RESD/check-mode/driver.log 2>&1); echo rc=$?
#    Expected: rc 0 and "CHECK ok: <n> supported models" in driver.log.
# 3. Launch W (sleeps until NOT_BEFORE; the peer gate refuses while a runtron of ours runs: launch between run 1's verdict and run 2's smokes, or after run 2):
#    option (a) (run 2 on 2026-10-13 from 13:00 UTC; W after the chain's hand-off marker is gone):
#      EXPECTED_BASE=<version> EXPECTED_BASE_SHA=<sha256> NEED_FLOOR_S=1800 NOT_BEFORE=2026-10-13T13:05:00Z DEADLINE_START=2026-10-14T01:35:00Z PASS_DEADLINE=2026-10-14T01:40:00Z DRIVER_END_BY=2026-10-14T02:05:00Z bash ~/workspace/intel-AMX/exec/pr4ci-20261012/launch.sh
#    option (b) (run 2 tonight; W alone on 2026-10-13 after the nightly):
#      EXPECTED_BASE=<version> EXPECTED_BASE_SHA=<sha256> NEED_FLOOR_S=1800 NOT_BEFORE=2026-10-13T13:00:00Z DEADLINE_START=2026-10-13T19:00:00Z PASS_DEADLINE=2026-10-14T00:30:00Z DRIVER_END_BY=2026-10-14T02:05:00Z bash ~/workspace/intel-AMX/exec/pr4ci-20261012/launch.sh
# 4. Watch: exec/results/pr4ci-20261012/.status, status-history.log, exec/logs/pr4ci-20261012.log. Stop: kill -TERM <pid> (never while the chain holds the machine).
