#!/usr/bin/env bash
# people-check.sh - may jhan use delphi-3bda right now, or is Bill (or CI) using it?
# Run ON delphi-3bda (it reads /proc and loginctl). Prints one verdict line.
#   exit 0  FREE   nobody else is using the machine; go ahead (and claim it)
#   exit 1  WAIT   CI, a blackout, or Bill is using it; check again later
#   exit 2  YIELD  Bill arrived at about the same time as we did; back off
# Options: --claim "note"  on FREE, write /var/tmp/3bda-claim.$USER
#          --release       remove our claim file and exit 0
# Tunables (env): PEOPLE_OTHER=bill  SAME_TIME_MIN=15  KEYBOARD_IDLE_MIN=30  CLAIM_MAX_H=12
set -u
. ~/workspace/intel-AMX/exec/lib-guard.sh
OTHER=${PEOPLE_OTHER:-bill}
SAME_TIME_MIN=${SAME_TIME_MIN:-15}
KEYBOARD_IDLE_MIN=${KEYBOARD_IDLE_MIN:-30}
CLAIM_MAX_H=${CLAIM_MAX_H:-12}
ME=$(id -un); MY_CLAIM=/var/tmp/3bda-claim.$ME; NOW=$(date +%s)
stamp() { date -u -d "@$1" +%FT%TZ; }

if [ "${1:-}" = "--release" ]; then rm -f "$MY_CLAIM"; echo "RELEASED: removed $MY_CLAIM"; exit 0; fi

# 1. Nightly CI lease (authoritative for CI; see handoffs/check-CI.md).
if ci_lease_busy; then echo "WAIT: System CI holds the DUT (lease busy)"; exit 1; fi
# 2. Blackout window promised to someone (lib-guard.sh blackout_active).
if blackout_active 2>/dev/null; then echo "WAIT: blackout window active (see /var/tmp/jhan/3bda-blackout)"; exit 1; fi
# 3. A fresh claim file from the other person.
for f in /var/tmp/3bda-claim.*; do
  [ -e "$f" ] || continue
  u=${f##*.}; [ "$u" = "$ME" ] && continue
  age=$(( NOW - $(stat -c %Y "$f") ))
  if [ "$age" -lt $(( CLAIM_MAX_H * 3600 )) ]; then
    echo "WAIT: $u claimed the machine at $(stamp $(( NOW - age ))): $(cat "$f")"; exit 1
  fi
done
# 4. Login age of the other person (loginctl sees ssh sessions with or without a tty).
newest_login=0
for s in $(loginctl list-sessions --no-legend | awk -v u="$OTHER" '$3==u {print $1}'); do
  t=$(loginctl show-session "$s" -p Timestamp --value) || continue
  e=$(date -d "$t" +%s 2>/dev/null) || continue
  [ "$e" -gt "$newest_login" ] && newest_login=$e
done
if [ "$newest_login" -gt 0 ]; then
  login_age_min=$(( (NOW - newest_login) / 60 ))
  my_claim_age_min=-1
  [ -e "$MY_CLAIM" ] && my_claim_age_min=$(( (NOW - $(stat -c %Y "$MY_CLAIM")) / 60 ))
  if [ "$login_age_min" -lt "$SAME_TIME_MIN" ]; then
    if [ "$my_claim_age_min" -ge "$SAME_TIME_MIN" ]; then
      echo "HOLD: $OTHER logged in $login_age_min min ago but our claim is $my_claim_age_min min old; tell $OTHER we are mid-run"
      exit 0
    fi
    echo "YIELD: $OTHER logged in $login_age_min min ago (arrived together); releasing our claim"
    rm -f "$MY_CLAIM"; exit 2
  fi
fi
# 5. At the keyboard: tty idle below the threshold counts as active use even at 0 CPU.
while read -r _ line _ _ idle _; do
  case "$idle" in
    .) echo "WAIT: $OTHER is typing on $line (tty idle < 1 min)"; exit 1 ;;
    old|'') ;;
    *:*) m=$(( 10#${idle%%:*} * 60 + 10#${idle##*:} ))
         [ "$m" -lt "$KEYBOARD_IDLE_MIN" ] && { echo "WAIT: $OTHER at keyboard on $line (tty idle $idle)"; exit 1; } ;;
  esac
done < <(who -u | awk -v u="$OTHER" '$1==u')
# 6. Programs doing real work (CPU over a 10 s window, or tron/build binaries).
if GUARD_OTHER_USERS=$OTHER other_user_active; then echo "WAIT: $OTHER has programs running (see GUARD line above)"; exit 1; fi

note="idle login" ; [ "$newest_login" -eq 0 ] && note="not logged in"
echo "FREE: $OTHER $note, no CI lease, no blackout, no claim"
if [ "${1:-}" = "--claim" ]; then
  printf '%s since %s: %s\n' "$ME" "$(stamp "$NOW")" "${2:-working}" > "$MY_CLAIM"
  echo "CLAIMED: wrote $MY_CLAIM ($(cat "$MY_CLAIM"))"
fi
exit 0
