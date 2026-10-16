# CI Team Handoff: Xeon 6 SST Setting For Tron CI Inference

## Change To Make

On matching Tron CI inference nodes, configure Intel Speed Select this way before running the CI benchmark/service:

- `turbo-freq`: **disabled**
- `core-power`: **disabled**

This is a Linux-side runtime/provisioning setting using `intel-speed-select`. No BIOS change was required for the winning configuration in this run.

## Why CI Should Change

For the tested profile (`llama-3.2-3b-instruct-fast-tp2`, TP=2, 32 users, 4 runtron instances), disabling SST `turbo-freq` changed the CPU from one fast domain plus three slow domains into a uniform high-frequency all-domain shape.

Measured result after baseline -> candidate -> restored baseline:

| Metric | Average baseline | Candidate | Change |
|---|---:|---:|---:|
| Gen/decode TPS per machine | 4655.4 | 5236.6 | +12.48% |
| Parse/prefill TPS per machine | 37040.1 | 47592.4 | +28.49% |
| Avg_Bzy_Mhz | 2830 | 3801 | +34.3% |
| Gen TPS/W | 12.30 | 12.93 | +5.1% |
| Parse TPS/W | 97.88 | 117.48 | +20.0% |

Baseline reproducibility check passed: restored baseline was within 0.24% gen and 0.15% parse of the first baseline.

## Installation

Install or build `intel-speed-select` on the CI image. The tested binary was built from Linux v6.8 `tools/power/x86/intel-speed-select` and preserved in the run workspace. For production, install it under a stable path such as:

```bash
/opt/intel-speed-select/intel-speed-select
```

Example build from the Linux v6.8 source tarball:

```bash
sudo apt-get update
sudo apt-get install -y build-essential curl xz-utils pkg-config libnl-3-dev libnl-genl-3-dev

WORK=/tmp/intel-speed-select-build
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

curl -fL -o linux-6.8.tar.xz https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.8.tar.xz
tar -xf linux-6.8.tar.xz

make -C linux-6.8/tools/power/x86/intel-speed-select

sudo install -D -m 0755 \
  linux-6.8/tools/power/x86/intel-speed-select/intel-speed-select \
  /opt/intel-speed-select/intel-speed-select

/opt/intel-speed-select/intel-speed-select --help
```

If the CI image already builds from a checked-out Linux source tree, the equivalent build step is:

```bash
make -C <linux-source-tree>/tools/power/x86/intel-speed-select
sudo install -D -m 0755 \
  <linux-source-tree>/tools/power/x86/intel-speed-select/intel-speed-select \
  /opt/intel-speed-select/intel-speed-select
```

Use the upstream build above for production. The locally preserved test binary used a minimal v6.8 source snapshot with HFI/OOB daemon code omitted to avoid installing libnl development packages; that was acceptable for this experiment, but production CI should prefer the normal upstream tool build with the package dependencies installed.

Load the required Intel SST interface modules at boot or before applying the setting:

```bash
sudo modprobe isst_if_mbox_pci
sudo modprobe isst_if_mmio
sudo modprobe isst_tpmi
```

The node should have `/dev/isst_interface` present after module load.

`modprobe` is per boot. After a reboot, the CI team must either run the `modprobe` commands again before applying the SST setting, or make module loading persistent. Recommended persistent setup:

```bash
sudo tee /etc/modules-load.d/intel-sst.conf >/dev/null <<'EOF'
isst_if_mbox_pci
isst_if_mmio
isst_tpmi
EOF
```

Then reboot one node and verify:

```bash
ls -l /dev/isst_interface
lsmod | grep -E 'isst_if_mbox_pci|isst_if_mmio|isst_tpmi'
```

If the device node is missing, keep the node out of the CI pool and fail the provisioning check.

## Apply Setting

For the tested host topology, the representative power-domain anchor CPUs were:

```bash
ANCHORS="0 24 48 72 96 120"
ISST=/opt/intel-speed-select/intel-speed-select
```

Apply candidate setting:

```bash
for cpu in $ANCHORS; do
  sudo $ISST -c "$cpu" core-power disable
  sudo $ISST -c "$cpu" turbo-freq disable
done
```

Rollback/restored-baseline setting:

```bash
for cpu in $ANCHORS; do
  sudo $ISST -c "$cpu" turbo-freq enable
  sudo $ISST -c "$cpu" core-power disable
done
```

Do not blindly copy the anchor list to a different SKU/topology. Pick one online CPU per participating CPU power domain, then verify the readback output shows the expected package/die/powerdomain coverage.

## Verify Setting

Run readback after boot and before admitting the node to the CI pool:

```bash
for cpu in $ANCHORS; do
  sudo $ISST -c "$cpu" core-power info
  sudo $ISST -c "$cpu" perf-profile info
done
```

Expected candidate readback on each anchor:

```text
clos-enable-status:disabled
speed-select-turbo-freq:disabled
speed-select-core-power:disabled
```

If `speed-select-turbo-freq` is `enabled`, the node is in the slower baseline mode for this workload.

## Runtime Validation

After rollout, run the standard CI workload and validate:

- all runtron instances return code 0;
- error rate is 0;
- gen/decode TPS is near the candidate band, about 5237 machine tok/s or 161-165 per-user tok/s;
- package power/thermals are acceptable for the node, around 405 W in this test profile;
- optional turbostat check: `Avg_Bzy_Mhz` should be around 3800, not around 2830.

## Persistence

This setting should be asserted by provisioning or a systemd oneshot after boot. Treat readback failure as node-health failure and keep the node out of the CI pool until corrected.

## Scope Limit

Apply this to the matching Tron CI multi-instance inference workload class. Do not assume it helps lightly threaded, single-stream, or latency-critical workloads; those may benefit from SST-TF's asymmetric high-priority turbo behavior and need separate testing.

## Supporting Quotes

Intel RDT spec explains the CLOS idea used by core-power priority controls: "resource allocation based on Class of Service (CLOS) tags" and that software can "specify a CLOS when an application, thread or VM is scheduled".

The `intel-speed-select` tool source describes `turbo-freq` as the ability to "set different turbo ratio limits to cores based on priority" and `core-power` as defining "per core/tile priority".
