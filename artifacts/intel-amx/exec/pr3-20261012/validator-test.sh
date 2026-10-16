#!/usr/bin/env bash
# The four fixtures of PR3-handoff.md step 6 D for validate-smoke.py: complete (ok), a 1-token file, one arm with 255 tokens,
# a missing "smoke <arm> rc=" line (all three must fail). Output: validator-test.log.
D=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d /tmp/pr3-validator.XXXXXX)
mk() { local dir=$1 n=$2 norc=$3 arms="base new new2 newoff head"; mkdir -p "$dir"; : >"$dir/smoke.txt"
  for a in $arms; do [ "$norc" = "$a" ] || echo "smoke $a rc=0 Version: x" >>"$dir/smoke.txt"; seq -s' ' 1 $([ "$a" = new ] && echo "$n" || echo 256) >"$dir/$a.tokens"; done; }
{ mk "$T/ok" 256 -; printf 'ok     %s\n  rc=%s\n' "$(python3 "$D/validate-smoke.py" "$T/ok" 256 base new new2 newoff head)" "$?"
  mk "$T/one" 1 -; printf 'one    %s\n  rc=%s\n' "$(python3 "$D/validate-smoke.py" "$T/one" 256 base new new2 newoff head)" "$?"
  mk "$T/short" 255 -; printf 'short  %s\n  rc=%s\n' "$(python3 "$D/validate-smoke.py" "$T/short" 256 base new new2 newoff head)" "$?"
  mk "$T/norc" 256 new; printf 'norc   %s\n  rc=%s\n' "$(python3 "$D/validate-smoke.py" "$T/norc" 256 base new new2 newoff head)" "$?"
} | tee "$D/validator-test.log"
rm -rf "$T"
