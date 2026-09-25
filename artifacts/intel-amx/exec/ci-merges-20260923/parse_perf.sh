#!/bin/bash
# usage: parse_perf.sh <log> <night>; prints CSV rows: night,tron,model,users,prompt,gen,ttft_ms,tps
log=$1; night=$2
sed 's/\x1b\[[0-9;]*m//g' "$log" | sed 's/^system_ci\tUNKNOWN STEP\t//' | awk -v night="$night" '
/Setting up tron \(/{tv=$0; sub(/.*Setting up tron \(/,"",tv); sub(/\).*/,"",tv)}
/n_users=/{u=$0; sub(/.*n_users=/,"",u); sub(/,.*/,"",u)}
/ prompt_length=/{p=$0; sub(/.*prompt_length=/,"",p); sub(/,.*/,"",p)}
/generate_length=/{g=$0; sub(/.*generate_length=/,"",g); sub(/,.*/,"",g)}
/Running averages:/{ra=$0; sub(/.*TTFT=/,"",ra); tt=ra; sub(/,.*/,"",tt); tp=ra; sub(/.*TPS=/,"",tp)}
/Perf test for .* completed in/{m=$0; sub(/.*Perf test for /,"",m); sub(/ completed in.*/,"",m); printf "%s,%s,%s,%s,%s,%s,%s,%s\n", night, tv, m, u, p, g, tt, tp; tt=""; tp=""}
'
