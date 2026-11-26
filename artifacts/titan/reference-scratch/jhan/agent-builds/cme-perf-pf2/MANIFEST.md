# cme-perf pf2: MANIFEST

`cme-perf-pf` (gated PASS) with the pf rows reordered (SMS first, SPM last) and the stream's RPRFM overshoot cleaned: a new `cme_perf` and `rows.sh`. **Not launched.** Built on LSF (job 567831) by `fvp-smoke/pf-build.sh`.

| Item | Identity | sha256 |
|---|---|---|
| `cme_perf` | asimov-bench feature/cme-perf-pr3 `60a379c` (local, not pushed: `94e47c2`, `298ba81`, `9328b56`, `60a379c`), `src-06121737e30e`; `stream` mode (overshoot cleaned), `--mem spm`; `gdn_rows`, `gdn_rows_nopf`, `gdn_rows_il` unchanged | `8e52271635d8e3a8e7e01e56378953ea196d61cea00ace93d251e9653f32983f` |
| `rows.sh` | same commit; `rows_pf` (SMS, OCM, SPM), `rows_fvp_pf`, `rows_fvp_pf_spm` | `e79d797d432e203ccc98b34289b5fe66076dc22145944d2160d76504672bc3a7` |
| `init.sh` | = cme-perf-pf; adds the 4 SPM column windows (Normal-NC) to `spm_dma_map` and the pf sets | `f86f93894d51c937567c2b3cb523ae9b5dc72f560ae3426cee593a93741711e3` |
| `check_cme_perf.py` (not in the boot) | asimov-bench `60a379c` | — |
| `in.bin`, `expected-za.bin`, `expected-sve.bin` | = cme-perf-isa2 | — |
| `spm_dma_map.ko` | = cme-perf-isa2 | `578fd6b0acec01f6163d37efff6778bc1555e05383f32a0ce507de0a82338552` |
| SCP BL1 / BL2 | scp-v0.40.0 (4f31d5d), debug, = cme-perf-isa2 | `d773832e…` / `21b3876d81d5dfe041ef01ed42469c60090aa9e20321955ee3f44ca337304aa4` |
| BL31, kernel Image | asimov-os v0.0.13 release (composite bytes 0 – 0x1FFFFFF equal to cme-perf-pf and cme-perf-isa2) | in the composite |
| `ap_composite.bin` | | `513e8acbd0d7f7464651160fd2481cec3a24ab15a4cc2c1a0ee0b141db19186d` |
| `ap_composite.bin.sms` | | `db88760023559a7bd0d64e631ae21b37ed0c78b9f37f8f63ac28c323c8e1d334` |
| `asimov.dtb` | bootargs `… rdinit=/cme-perf/init.sh cme_perf.rows=pf`; otherwise only `linux,initrd-end` differs from cme-perf-pf | `f9a8e123f5fe3cc965ae2c86e7fdad50aa60939b606bd8a9de20f99f3a9275e8` |
| `rootfs.cpio.lz4` | v0.0.13 rootfs + `/cme-perf` | `60246c5b61972a3eb42c063c357b5555946fd009bde0695943e40abc4a710454` |
| SMS profile | = cme-perf-isa2 | `e68ec172f769651d04c6a3fcb288a35f0cfa0a9e27ca2b6f007038f74a2d34a9` |

Target: GA13 `hemi_rtws_tlm` (asimov release a10181848), clone 2, 4 boards, as #4007, with `--run-cycles 5000000000`. The launch needs Jacob's go (decision 63 covers it); the lead enqueues it after the verifier's PASS.

`SHA256SUMS` lists every file of this directory, `fvp-smoke/` included.
