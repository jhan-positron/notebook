#!/bin/bash
# Run the lld-linked binaries with a library path applied ONLY to them (not to the shell tools); glibc dirs excluded.
M=/var/tmp/jhan/memorder
CXX=/nix/store/nzk8s2vc3k10mp4xcimvhq7r6w6kiwjv-clang19-wrappers/bin/clang++-19
LP=""
add() { d=$1; [ -d "$d" ] || return; [ -e "$d/libc.so.6" ] && return; case ":$LP:" in *":$d:"*) ;; *) LP="${LP:+$LP:}$d";; esac; }
for d in $(echo "${NIX_LDFLAGS:-}" | tr ' ' '\n' | grep '^-L' | sed 's/^-L//'); do add "$d"; done
add "$(dirname "$($CXX -print-file-name=libstdc++.so.6)")"
for i in 1 2 3; do
  for lib in $(LD_LIBRARY_PATH="$LP" ldd $M/t_assert_OLD 2>/dev/null | awk '/not found/{print $1}'); do
    p=$(find /nix/store -maxdepth 3 -name "$lib" -print -quit 2>/dev/null); [ -n "$p" ] && add "$(dirname "$p")"
  done
done
echo "LD_LIBRARY_PATH entries: $(echo "$LP" | tr ':' '\n' | wc -l); still missing: $(LD_LIBRARY_PATH="$LP" ldd $M/t_assert_OLD 2>/dev/null | grep -c 'not found')"
for b in probe_old_assert_lld t_assert_OLD t_assert_FIXED; do
  echo; echo "### $b"
  LD_LIBRARY_PATH="$LP" $M/$b > $M/$b.out 2>&1; rc=$?
  sed 's/\x1b\[[0-9;]*m//g' $M/$b.out | grep -v '^\s*$' | tail -9; echo "exit=$rc"
done
