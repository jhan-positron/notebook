# Goldcrest AVIP timing

The 32 embedded Goldcrest datapath lanes use the existing Cadence AXI AVIP
register bank for response latency and an emulation-only service scheduler for
bandwidth and refresh pauses. XMS accesses these memories through AXI. The four
AUX lanes are also embedded memories, but host timing settings apply only to
the 32 datapath lanes. Timing is
available in the ordinary embedded-memory/Gauntlet build. It needs no timing
build switch or separate image variant. The scheduler is part of the emulation
wrapper; Asimov compute RTL and AVIP backing storage are unchanged.
Ordinary hemisphere simulation and `--noegc` emulation use reactive memory
and reject native timing settings. The focused Xcelium qualification directly
instantiates an embedded AVIP lane.

Host-program `load_blob` and `scatter` operations with `ddr_timing: true`
enter the real XMS AXI interfaces and use this same timing model and service
budget. Omitted/false keeps direct backdoor initialization for KV cache and
learned parameters. The [host transport contract](HOST_PROGRAM_V1.md#host-ddr-timing)
defines grouping, routing and completion. There is no separate host DDR
calendar or additional software latency on timed writes.

## Native AVIP controls and added emulation logic

The host exposes both kinds of controls through `goldcrest_timing`, but they
are implemented by different components:

| Capability                            | Implementation                    |
| ------------------------------------- | --------------------------------- |
| AXI READY delays and response latency | Existing Cadence AVIP             |
| Read/write response burst gaps        | Existing Cadence AVIP             |
| Native outstanding-request limits     | Existing Cadence AVIP             |
| Shared R/W and directional byte rates | Added emulation service scheduler |
| Periodic whole-pool refresh pauses    | Added emulation service scheduler |
| Read buffering and public read limit  | Added emulation lane wrapper      |
| Reset defaults                        | Added emulation lane wrapper      |
| Package controls and bank programming | Added host software               |
| Timed host issue through XMS AXI      | Added asynchronous host driver    |

**Cadence implements the native delays.** The host writes existing controls
in slave_bfm.delay_cfg_reg_blk; the Cadence BFM generates the requested READY,
first-response and burst-gap timing. The
[native parameter table](#native-cadence-avip-parameters) lists those fields.

**Bandwidth and refresh require logic added by this repository.**
[hemi_gc_service_scheduler](../agents/hemi_gc_service_scheduler.sv) maintains
byte credits and a periodic refresh timer.
Its controls live in the separate five-word service_cfg bank, described in
[added service parameters](#added-bandwidth-and-refresh-parameters).
[hemi_gc_lane_service](../agents/hemi_gc_lane_service.sv) accounts for read
sizes/IDs and write strobes and gates AXI beat service. The
[Goldcrest emulation wrapper](../agents/goldcrest_ew_fullconn_avip.sv) also adds
a two-beat read buffer and keeps the public read-outstanding count aligned
with the native limit, including responses held in that buffer. Bandwidth or
refresh can therefore delay a response beyond the native minimum latency.

The reset profile below is selected and restored by our wrapper; these values
are not Cadence's built-in defaults. The
[host adapter](../sim/hemi_gc_wmem_preload.cpp) validates requested settings
and programs both banks through the existing MARG interface. Host programs apply
overrides after serial initialization's existing reset wait; no configuration
readiness handshake or reset watchdog is added.
This support logic, the service scheduler and the read buffer are emulation
additions. The backing memory remains in the native Cadence BFM.

## Startup and reset contract

The HEMI wrapper loads this provisional optimistic profile at power-on and on
**every datapath lane reset**:

| Control                                 | Reset value                                     |
| --------------------------------------- | ----------------------------------------------: |
| Minimum read latency                    | 61 AXI cycles (40 ns transport + 21 ns row hit) |
| Minimum B-response latency              | 40 AXI cycles (posted response transport)       |
| Read/write outstanding limits           | 63 each                                         |
| AW/AR/W READY delays and B/R burst gaps | 0                                               |
| Read ordering/interleaving words 7/8    | 0 (native defaults)                             |
| Older packed timing override            | 0 (disabled)                                    |
| Shared read/write service               | 39322 bytes / 1024 AXI cycles (~38.4 GB/s)      |
| Each direction's link service           | 43200 bytes / 1024 AXI cycles                   |
| Refresh interval / duration / phase     | 3900 / 0 / 0 AXI cycles                         |

The reset is the AVIP lane's active-low `ARESETn`, connected to the Goldcrest
wrapper's `rstn_i`. A reset that does not reach that pin does not restore the
profile. Reset flushes AXI transactions, including pending responses, without
clearing the backing memory. Data from an incomplete write is not guaranteed.
The four AUX lanes retain native zero-delay startup and programmed-control
retention across reset.
Instances without a HEMI pair index, including the current FC integration,
also retain that existing behavior. These instances elaborate neither the
added timing-bank initialization/reset processes nor the service MARG map.

**Reset restores defaults. Program non-default settings after reset release,
before traffic, and reapply them after every subsequent lane reset.** Writes
during active reset can be overwritten by the reset defaults. Keep reset stable
and AXI traffic drained while programming. The host does not track whether a bank
is fresh or previously programmed, or automatically restore overrides after reset.

Programs with `goldcrest_timing` must start with `load_blob` targeting
`serial_config`, and use **release-all boot** (`hemi_release_boot` or the default
fast-simulation release), releasing TWS, SPM, XMS and HRA together. The existing
[serial initializer](../sim/hemi_serial_cfg_test.cpp) waits for TWS/SPM readiness
and then 200 core clocks. Under this release policy, Goldcrest's longest reset
path takes at most 198 core clocks: 49 for XMS distribution, 129 for local reset
stretch/release, and up to 20 for APB sampling. Independent XMS/HRA reset holds or
later software resets are outside that startup guarantee.

After complete plan validation, the host claims metadata and runs the first
serial initializer. Only after it succeeds does the host apply timing overrides,
before executing the remaining operations. Missing or misordered initialization
is rejected before target I/O; failed initialization skips timing programming.
No additional reset poll, readiness signal or fixed delay is introduced.

When `goldcrest_timing` is omitted, startup performs no timing-bank access,
validation, programming or reporting. The resident settings remain in effect;
after reset those are the defaults above. The reactive backend also accepts
packages without timing overrides, and these packages still may omit serial
initialization. Explicit settings trigger validation and readback on every DP
lane after initialization and before workload traffic.

Host settings change only the requested controls before workload traffic and
remain effective until the next lane reset. An omitted field leaves its
resident value unchanged; a new workload alone does not restore the defaults.
Set a delay explicitly to zero to remove it. Set both bandwidth rates and the
refresh duration to zero to bypass service scheduling as well. Restoring an
emulator snapshot restores its saved settings; it is not a fresh reset. Zero added delay still
includes the native transaction/memory pipeline.

### Basis and limits of the optimistic profile

This is a tunable **optimistic engineering estimate**, not calibrated
Goldcrest timing or a proven hardware performance bound. The owning physical
assumptions are:

| Component         | Evidence or estimate                                   | Modeled treatment          |
| ----------------- | ------------------------------------------------------ | -------------------------- |
| Remote round trip | Credo advertises 40 ns; newer article says about 50 ns | 40 ns once per response    |
| Read row hit      | gem5 LPDDR5-6400 reference: 21.25 ns                   | 21 ns added to transport   |
| Memory bandwidth  | Assumed x32 LPDDR5X at 9.6 GT/s                        | 38.4 GB/s shared R/W       |
| Link bandwidth    | Three 112.5 Gb/s lanes per direction                   | 42.1875 GB/s/direction     |
| Posted B response | Controller can acknowledge accepted, ordered writes    | Transport without tWR      |
| Refresh           | Available banks hide refresh in the optimistic case    | No forced whole-pool pause |

Credo's [Weaver product brief](https://credosemi.com/wp-content/uploads/Credo-OmniConnect-Weaver.pdf)
specifies 40 ns round-trip latency and a 9.6 GT/s LPDDR5X PHY. Its
[October 2026 technical article](https://credosemi.com/blogs/breaking-the-memory-wall-how-omniconnect-decouples-memory-from-compute/)
says about 50 ns including FEC, without explaining the difference. The default
uses the lower advertised figure; increase read/B latency by 10 cycles to
measure sensitivity to the higher figure. These are transport figures, not
complete DRAM access latency. No extra on-die XMS delay is added here because
that path is already executed by RTL.

The read component comes from the public
[gem5 LPDDR5-6400 reference](https://gem5.googlesource.com/public/gem5/+/refs/heads/stable/src/python/gem5/components/memory/dram_interfaces/lpddr5.py)
(`LPDDR5_6400_1x16_BG_BL32`, source blob
`f35bef15aeba463ed15de2abaf0c14e944aac5cf`). Rounding 21.25 ns down to 21 ns
keeps this component optimistic. This is a representative timing reference,
not the unidentified Goldcrest DRAM part's datasheet. Native AXI reads assume
an open row and available banks; they do not charge ACT/PRE on every request.
The 40-cycle B default represents a posted response, not physical write
recovery. Acceptance of write data and later read visibility remain governed
by the native memory's AXI ordering and the testbench's checked payloads.

`design/xms/rtl/xms_clk_gen.sv` divides the 2 GHz source by two for LLD.
The vendor drop's `EW_FE_R1_0V1_71/sdc/IP.sdc` also specifies 1 ns AXI
clocks; `release_notes.txt` and `verilog_model/sim/test.v` use three
112.5 Gb/s SerDes lanes per logical link. The NS drop's
`Weaver_FPGA_model/sdc/weaver_chip_fpga.sdc` maps Goldcrest_ip0/1 AXI0/1 to
four separate DDR0..3 blocks. Its `model/Weaver.vp` exposes separate x32 DQ
interfaces. This supports independent lane pools; the final board wiring,
DRAM organization and configured data rate still need confirmation. The FPGA
model removes the DDR controller/PHY, so it cannot calibrate their timing.

At x32 and 9.6 GT/s, raw DRAM capacity is 38.4 GB/s **shared by reads and
writes**. The service register uses ceil(38.4 * 1024) = 39322, or
38.400390625 GB/s at 1 GHz: an upward approximation below 0.002%. The separate
42.1875 GB/s link budgets are retained; full-duplex link capacity does not
double the shared DDR budget. One pool is instantiated per AXI lane, with
no invented cross-lane sharing or clock-domain coupling.

Short bursts may use at most 64 idle-credit bytes per direction and 128
shared bytes; idle time cannot accumulate an unbounded future burst.
Fractional rates are preserved. Arbitration rotates between reads and writes
and reserves credit for a waiting large beat so narrow beats cannot starve it.
The DP AVIP compiles 64 response slots and defaults to 63 outstanding requests.
These are emulation bookkeeping slots, not a claim of 63 DDR queue entries.
A 15-request window with 61 ns latency would cap 64-byte reads near 15.7 GB/s
before memory service; the larger window avoids that artificial bottleneck.

Read cost follows ARSIZE, the partial first beat of an unaligned INCR transfer,
and the repeated byte range of FIXED transfers. Reused IDs retain request
order; distinct IDs may complete out of order. Write cost is the WSTRB byte
count. Costs omit physical DRAM burst granularity, read-modify-write and link
framing. That is an optimistic payload-service approximation. A transparent
two-beat read buffer breaks AVIP handshake feedback without adding an unloaded
latency cycle; the public outstanding limit still includes those buffered
responses. An exposed beat retains its grant through backpressure and refresh.
B responses use the native transport-latency setting; no tWR penalty is added.
This does not model a controller's deeper posted-write buffers or policy.

### Refresh policy and accuracy limit

`refresh_duration_cycles > 0` enables periodic **whole-pool** pauses. Every
`refresh_interval_cycles`, new nonempty read/write service stops for that
many cycles; already granted beats may finish. The first pause starts after
`interval - phase` cycles following a configuration change. The calendar runs
while traffic is idle, and unused bandwidth does not accumulate during a
pause. Lane reset clears the calendar and restores the profile. Settings must
change with AXI traffic drained; setting the same values does not restart the
calendar or refill credits. A zero duration disables pauses.

Refresh duration defaults to **zero deliberately**, while read/B latency and
shared DDR bandwidth remain nonzero. A fixed whole-pool pause is not an established
optimistic Goldcrest default: per-bank refresh can leave other banks serving
traffic and can hide its cost, as described in
[AMD's LPDDR5 refresh options](https://docs.amd.com/r/en-US/pg456-integrated-mc/LPDDR5/5X-Refresh-Options).
For an explicit all-bank sensitivity experiment, AMD documents 280 ns for
16 Gb devices; 280 / 3900 cycles at 1 GHz is a representative profile. These
values do not identify the Goldcrest DRAM part or establish its refresh policy.

Bank/row scheduling, per-bank refresh overlap, refresh postponement,
read/write turnarounds, link overhead and physical cross-lane sharing remain
unmodeled. Calibrating those requires the attached DRAM part, controller policy
and channel map. Cadence's separate
[LPDDR5 memory VIP](https://www.cadence.com/en_US/home/tools/system-design-and-verification/verification-ip/simulation-vip/memory-models/dram/lpddr5.html)
models DRAM commands; these features are not native AXI AVIP controls.

## Configure a Gauntlet workload

The optional `goldcrest_timing` object in
`hardware/host_program/program.json` carries settings through the existing
Gauntlet `.tron` transport. The host validates them and uses MARG to program
only the specified native/service words on all 32 datapath lanes. All lane
handles, geometries and initial reads are checked before the first write.
Partial updates are merged with every lane's resident state, and all resulting
profiles are validated before any lane is written. **Begin the program with
`load_blob` targeting `serial_config`, and use release-all boot as specified in
the [startup contract](#startup-and-reset-contract).** The package tool, stager
and host executor reject overrides without that first operation. Package-level
settings are applied after its successful reset wait and replay, before the
remaining operations. Upstream master reset completion alone is insufficient.
Hold resets stable while configuring and running a workload; after any lane
reset, reapply non-default settings before resuming traffic. Full-bank
readback must match the requested update with every unrequested word preserved.
Any programming failure stops execution before the remaining workload operations.
Programming is not atomic across lanes or words. After a write/readback failure,
reset the lanes and reapply the desired settings before traffic; the host does
not roll back partial writes. Successful programming prints the resident controls
for all 32 lanes, followed by
`[gc-avip] timing readback PASS lanes=32`.

Create a new package from an existing workload:

```bash
python3 -B emu/hemi_tlm/scripts/configure_gc_timing.py \
  decode.tron decode-latency.tron \
  --read-latency-cycles 200 --read-burst-gap-cycles 8 \
  --read-outstanding 8
/tools/gauntlet run-host-program --tron decode-latency.tron --build 'GA13#4'
```

The example values are synthetic tuning values, not calibrated Goldcrest
measurements. Select the actual site-qualified build available for the run.
The helper validates the original package, updates its timing settings and
program digest, and preserves all workload operations and artifact payloads.
It refuses to overwrite an existing output. Other settings already present in
the source package remain in the new package. The resulting program hash,
package hash and settings are recorded by the staging flow.

For example, the package contains:

```json
"goldcrest_timing": {
  "read_latency_cycles": 200,
  "read_burst_gap_cycles": 8,
  "read_outstanding": 8
}
```

To clear the delays in that example, create another package with
`--read-latency-cycles 0 --read-burst-gap-cycles 0`. Omission alone does not
clear a value left in a running model.

Updated host software/staging support is required to consume the optional
object. The reset defaults and service bank require a new ordinary model
build; an older image without the required banks rejects host timing overrides
before traffic. After that build, timing changes require no model rebuild.

## Controls

All delays are nonnegative integer **AXI clock cycles**, independently of the
core-clock waits used by host operations. Bandwidth is integer bytes per 1024
AXI cycles: `rate / 1024` GB/s at 1 GHz. Convert physical latency using the
actual AXI frequency of the selected image. The delay width is 16 bits and the
compiled native outstanding limit is 64 for datapath lanes and 16 for AUX.

### Native Cadence AVIP parameters

These package fields program the existing slave_bfm.delay_cfg_reg_blk bank.
Their delay and acceptance behavior is provided by Cadence AVIP; the wrapper
also applies the read limit at the public interface while buffering is active.

| Package field                   | Native word | Range    | Native meaning                                         |
| ------------------------------- | ----------: | -------: | ------------------------------------------------------ |
| `awready_delay_cycles`          | 0           | 0..65535 | AWVALID to AWREADY delay                               |
| `arready_delay_cycles`          | 1           | 0..65535 | ARVALID to ARREADY delay                               |
| `wready_delay_cycles`           | 2           | 0..65535 | WVALID to WREADY delay                                 |
| `write_response_gap_cycles`     | 3           | 0..65535 | Delay before a ready write response asserts BVALID     |
| `read_burst_gap_cycles`         | 4           | 0..65535 | Delay before the first RVALID of each ready read burst |
| `write_response_latency_cycles` | 5           | 0..65535 | Minimum from the later AW/last-W handshake to BVALID   |
| `read_latency_cycles`           | 6           | 0..65535 | Minimum AR handshake to first RVALID delay             |
| `read_outstanding`              | 9           | 1..63    | Native accepted read-burst limit                       |
| `write_outstanding`             | 10          | 1..63    | Native accepted write-burst limit                      |

Words 7/8 (read ordering and interleaving) are not modified by the host timing
interface. DP reset words 9/10 select 63; the compiled limit is 64.
In PDAPP2506.200, runtime writes of 0 or 64 do not restore that limit after
programming a lower value: the bank reads back the new word, but AXI acceptance
keeps the previous limit. The host therefore accepts only the qualified range
1..63. Reset selects the highest programmable limit so that lowering it remains
reversible. Leave a limit unspecified to preserve its resident value; lane
reset restores 63. Clearing delay controls does not restore a lowered limit.

### Added bandwidth and refresh parameters

These package fields program our five-word service_cfg bank and control the
added scheduler. They are not native Cadence AVIP parameters.

| Package field                  | Service word | Range     | Meaning                                            |
| ------------------------------ | -----------: | --------: | -------------------------------------------------- |
| `shared_bytes_per_1024_cycles` | 0            | 0..131072 | Aggregate R/W payload rate; 0 bypasses this budget |
| `link_bytes_per_1024_cycles`   | 1            | 0..65536  | Separate budget in each direction; 0 bypasses it   |
| `refresh_interval_cycles`      | 2            | 0..65535  | Time between whole-pool refresh pauses             |
| `refresh_duration_cycles`      | 3            | 0..65535  | Pause length; 0 disables refresh                   |
| `refresh_phase_cycles`         | 4            | 0..65535  | Initial calendar offset                            |

For a nonzero interval, duration and phase must each be smaller than the
interval. A zero interval requires zero duration and phase. Invalid merged
settings reject the workload before any programming write. The service bank
is beside `slave_bfm` in `g_embedded`.

For example, add these options to the packaging command for a **synthetic**
32 GB/s shared-memory experiment with all-bank reference refresh:

```text
--shared-bytes-per-1024-cycles 32768 --link-bytes-per-1024-cycles 43200
--refresh-interval-cycles 3900 --refresh-duration-cycles 280
```

### Host access to the two banks

The host carries both parameter groups in the same `goldcrest_timing` object
and programs their separate banks before workload traffic.
Unsupported fields, fractional values, Booleans and out-of-range values fail
validation. The normalized host plan contains one `GC_TIMING` record before
operations; the C++ executor independently validates it and rejects
unsupported transports.

The physical native AVIP bank path for lane `2*p+l` is:

```text
<top>.u_hemi_tlm.u_hemi.i_xms_top_wrapper.i_xms_top.g_gc_bind_phy[p]
  .u_goldcrest_lane.lane_bfm<l>.g_embedded.slave_bfm.delay_cfg_reg_blk
```

`<top>` is `sim_top` for simulation or `top` for emulation. The bank is eleven
32-bit words. The wrapper clears the older packed `delay_cfg_mem` override on
each DP reset so it cannot supersede the native bank. The separate five-word
service bank has suffix `service_cfg` at the same `g_embedded` path.
There is no configuration status word to poll or mark. Host programs and direct
MARG clients follow the same ordering contract: release lane reset, program and
read back the desired settings with traffic drained, then start traffic.
Every later lane reset restores defaults and requires reprogramming overrides.
Resets must remain stable throughout programming. Snapshot restore retains its
saved bank values; it does not imply a fresh reset.
The HEMI emulation-copy patch passes the existing `GC_PAIR_INDEX`
parameter to distinguish DP from AUX; compute RTL is unchanged.

Untimed host preloads and readbacks remain direct memory transfers. Timed host
loads/scatters follow the [XMS AXI transport contract](HOST_PROGRAM_V1.md#host-ddr-timing)
and share this model with hardware-issued accesses. Native/service settings
therefore govern both kinds of AXI traffic. The model begins at CMN egress;
software execution/cache misses and earlier CMN mesh traffic are outside that
boundary. Physical FEC overhead and controller policy remain uncalibrated.

## Qualification

`tests/run_xms_host_timing.sh <new-directory>` exercises the production timed
host driver against installed AVIP master callbacks, real XMS ingress blocks,
two real XIG gearboxes
and embedded Goldcrest lanes. It checks backdoor-initialized data followed by
partial/aliased writes, concurrent issue across both ports, shared service with
fetch reads, ID lifetime, and response/reset failures. Dedicated disjoint-byte
writes to the same word must have two outstanding requests per port and preserve
every neighboring byte. Negative controls corrupt payloads, widen partial-write
strobes, reuse a live write ID, serialize submissions or bypass the shared
budget. Its reduced topology checks the API, ingress, gearbox and shared service;
full XMS routing/arbitration requires the
hemisphere `--test ddr-timing` case described in
[Host DDR Timing Test](HOST_PROGRAM_V1.md#host-ddr-timing-test).

The focused suite is `tests/run_gc_avip_timing.sh <new-directory> all` and
requires authorization to run Xcelium. It compares complete public AXI traces
for the unwrapped native reference and the explicit-zero wrapper at matching
limits of 15, after programming completes. The zero profile is explicitly
reapplied after reset; nonzero startup is checked separately. This comparison
does not claim legacy zero startup or cap 16 for the new default profile.
Separate `defaults` scenarios check native startup
with service scheduling explicitly bypassed,
1/2/8/16/32/64-beat and mixed queued reads, exact first-data timing and overlap,
bank and effective-limit restoration over two resets, reset with pending R/B
responses or partial W data, restored READY/B settings measured at the pins,
memory reuse, writes overwritten during active reset, and reapplication of nonzero
and zero overrides after reset. Omitting the post-reset override must fail the
effective-latency check.
The `estimate` scenario checks the untouched combined profile: exact unloaded
61-cycle reads and 40-cycle posted B responses, continuous single-beat reads
and writes, and mixed traffic sharing the 38.4 GB/s pool. Independent negative
controls omit transport, restore the raw-link budget or shrink the response
window; each must fail its timing/throughput oracle.
The `service` scenario checks untouched nonzero service defaults, all burst
sizes, native narrow/unaligned/FIXED payloads, reused IDs, shared read/write
throughput, periodic refresh, read caps including buffered data, partial and
leading writes, held responses, reset restoration and subsequent bypass.
Removing either bandwidth budget or refresh must fail its dedicated checker.
`tests/run_gc_service_unit.sh <new-directory>` independently checks fractional
rates, unequal-width fairness, credit bounds, refresh timing, invalid profiles,
ID metadata through the 63-request boundary, narrow/unaligned costs and
independent pools at different clocks.
The `aux` scenario compares raw startup controls and complete AXI traces with
an untouched native AVIP reference. It checks zero effective startup delays,
compiled limits of 16, and retention of programmed latency/limits across reset.
The unused raw native control bank is uninitialized in four-state simulation;
effective native defaults do not require its contents to read as zero.

The `native` scenarios check all delay/gap controls, request limits through 63,
backpressure, strobes and changed-byte readback, 24 leading-W requests, and
return to zero. Negative controls remove reset latency, retain stale overrides,
serialize reads, add burst gaps, bypass delay/acceptance settings, accept requests
two cycles early, or corrupt stored payloads; each must fail its own checker.
Separate boundary reproducers retain the failing assertions for native 0/64
limit writes; the runner reports these as a confirmed vendor limitation.

`tests/test_gc_native_timing.py` runs the production stager, host executor and
MARG adapter with instrumented host-side banks. It checks all-lane mapping,
absence of bank access when settings are omitted, explicit zero, retention over
repeated startup, preservation of unrequested fields, package rewriting,
both timing banks, merged-profile validation, explicit service bypass, CLI
transport, failure before workload traffic, and reset/reprogram recovery after
a partial write. This proves host plumbing,
not target AXI latency. Neither host tests nor a small Xcelium wrapper run
establishes GA13 access or calibrated physical DDR behavior.
`tests/test_xms_adapter.py` exercises the production adapter's HRA mode reads
with distinct debug-counter contents, all decode modes and HRA-write cache
invalidation. `tests/test_real_gc_wrapper.py` checks that real-Goldcrest wrapper
generation extracts only the two manager-side BFMs.

The native register meanings above are from the installed PDAPP2506.200
`doc/vp_axi_avip_user_guide/Using_AVIP_with_Embedded_Slave_Interface.html` and
its `basic/test_slave_mem.cpp` example. The small suites use Xcelium 25.09-s004
and PDAPP2506.200. See their retained run logs for the tested source snapshot;
compile success alone is not a runtime verdict. Palladium compilation and
MARG access to the resettable banks remain target qualification work.
