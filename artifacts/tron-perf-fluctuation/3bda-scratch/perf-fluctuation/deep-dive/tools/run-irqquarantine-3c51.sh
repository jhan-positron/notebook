#!/bin/bash
# Intervention A/B: irqbalance stopped + all movable IRQs pinned to platform
# cores (0,72,144,216) for the campaign; full restore on exit.
set -u
ROOT=$1
SAVE=$ROOT/irq-affinity-save.txt
restore() {
  while IFS=: read -r irq aff; do
    echo "$aff" | sudo -n tee /proc/irq/$irq/smp_affinity_list >/dev/null 2>&1
  done < $SAVE
  sudo -n systemctl start irqbalance 2>/dev/null
  echo "$(date -u +%FT%TZ) IRQ affinities restored, irqbalance restarted: $(systemctl is-active irqbalance)" >> $ROOT/intervention.log
}
trap restore EXIT
sudo -n systemctl stop irqbalance
moved=0; failed=0
: > $SAVE
for d in /proc/irq/[0-9]*; do
  irq=$(basename $d)
  aff=$(cat $d/smp_affinity_list 2>/dev/null) || continue
  echo "$irq:$aff" >> $SAVE
  if echo "0,72,144,216" | sudo -n tee $d/smp_affinity_list >/dev/null 2>&1; then
    moved=$((moved+1))
  else
    failed=$((failed+1))
  fi
done
echo "$(date -u +%FT%TZ) irqbalance stopped; IRQs moved=$moved unmovable=$failed" >> $ROOT/intervention.log
SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7/bin/runtron | cut -d" " -f1)
env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=16 CAPTURE=none KVWAIT=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  bash $ROOT/harness.sh
