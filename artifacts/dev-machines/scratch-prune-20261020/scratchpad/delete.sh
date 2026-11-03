#!/bin/bash
set -u
SP="$1"; LOG="$SP/delete.log"
exec > >(tee -a "$LOG") 2>&1
echo "start $(date -u) host=$(hostname)"
echo "--- git pointers before deletion:"
for d in pr3244/head pr3244/base pdjn-wt tron-src systest-b2; do
  if [ -f "/scratch/jhan/$d/.git" ]; then echo "$d: $(cat /scratch/jhan/$d/.git)"; elif [ -d "/scratch/jhan/$d/.git" ]; then echo "$d: own .git directory"; else echo "$d: no .git"; fi
done
echo "--- 1. pftrace files"
n=0; miss=0; skip=0
while IFS= read -r p; do
  case "$p" in /scratch/jhan/*.pftrace) ;; *) echo "SKIP (outside or not pftrace): $p"; skip=$((skip+1)); continue;; esac
  if [ -f "$p" ] && [ ! -L "$p" ]; then rm -f -- "$p" && n=$((n+1)) || echo "FAIL: $p"; else echo "MISSING: $p"; miss=$((miss+1)); fi
done < "$SP/delete-pftrace.txt"
echo "pftrace removed: $n, missing: $miss, skipped: $skip  $(date -u +%T)"
echo "--- 2. directories and files"
while IFS= read -r p; do
  case "$p" in /scratch/jhan/*) ;; *) echo "SKIP (outside): $p"; continue;; esac
  if [ -L "$p" ]; then echo "SKIP (symlink): $p"; continue; fi
  if [ -d "$p" ]; then echo "rm -rf $p  $(date -u +%T)"; rm -rf --one-file-system -- "$p" && echo "  done $(date -u +%T)" || echo "  FAIL rc=$? $(date -u +%T)"
  elif [ -f "$p" ]; then rm -f -- "$p" && echo "removed file $p" || echo "FAIL file $p"
  else echo "MISSING: $p"; fi
done < "$SP/delete-dirs.txt"
echo "--- 3. verification"
echo "pftrace left under /scratch/jhan: $(find /scratch/jhan -type f -name '*.pftrace' 2>/dev/null | wc -l)"
for p in $(cat "$SP/delete-dirs.txt"); do [ -e "$p" ] && echo "STILL EXISTS: $p"; done
echo "df after: $(df -k /scratch | tail -1)"
echo "end $(date -u)"
