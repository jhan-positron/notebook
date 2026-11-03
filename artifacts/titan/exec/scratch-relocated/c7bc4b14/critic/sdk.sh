export LC_ALL=C
S=~/positron/src/phoenix-int
echo '--- README.md 218-228 (context of "count only from the perf host")'; sed -n '218,228p' $S/tools/conformance/README.md | cut -c1-400
echo '--- design 12-repository.md 48-58 and 248-256 (perf host definition, open question)'; sed -n '48,58p;248,256p' $S/docs/superpowers/specs/2026-09-24-sdk-v2-design-12-repository.md | cut -c1-600
echo '--- runtime-v2.md 334-337'; sed -n '334,337p' $S/docs/runtime-v2.md | cut -c1-500
echo '--- sampling tests: directories and presets'; ls $S/tests/cpp 2>&1 | tr '\n' ' '; echo; ls $S/tests/cpp/runtime 2>&1 | tr '\n' ' '; echo; grep -n -iE 'sampl' $S/CMakePresets.json | head -5; grep -rln -iE 'sampling' $S/tests/cpp --include=CMakeLists.txt 2>/dev/null | head -8
echo '--- test presets'; python3 -I -c "import json;d=json.load(open('$S/CMakePresets.json'));print([p.get('name') for p in d.get('testPresets',[])]);print([p.get('name') for p in d.get('buildPresets',[])])"
echo '--- fixture/compile logs (churn-r1 and check/r1)'; cat ~/positron/runs/churn-r1/record/fixture-dense.log; echo; cat ~/positron/runs/churn-r1/record/table-dense.log | cut -c1-300; echo; cat ~/positron/runs/churn-r1/record/model-fetch.log; echo; cat ~/positron/runs/churn-r1/record/core-build.log | head -12 | cut -c1-200
echo '--- run_scheduled_gate.sh churn branch 590-612'; sed -n '590,612p' $S/tools/ci/run_scheduled_gate.sh | cut -c1-220
echo '--- perf_job.sh 1-45'; sed -n '1,45p' $S/tools/perf/perf_job.sh | cut -c1-200
echo '--- harness record writer: who writes churn.record.json (grep in tools/conformance/churn.py and harness)'; grep -n -E 'record\.json|write_record|dump\(' $S/tools/conformance/churn.py | head -8; grep -rn -E 'record_path|\.record\.json' $S/tools/harness/*.c | head -5
