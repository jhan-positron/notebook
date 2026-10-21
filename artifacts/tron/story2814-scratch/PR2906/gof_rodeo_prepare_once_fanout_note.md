# PR2906 Note: GOF Rodeo Prepare-Once Fanout Experiment

This note records the experimental change that was tried and then backed out while
investigating Mike's suggestion to split `gof_rodeo_impl()`.

## Experiment

The current pre-split rodeo path prepares staging inside the target-shard loop:

```cpp
for each target shard:
  prepare_for_dma()
  xfer_gof()
  guard.commit()
  push()
```

The experiment changed the rodeo path to first count target shards that still need
the GOF/layer, then prepare staging once with a batch of DMA lifetime credits:

```cpp
count target shards
prepare_for_dma(..., xfer_count)
for each target shard:
  xfer_gof()
  commit_one()
  push()
```

Supporting change:

- `inflight_guard` was temporarily extended to own multiple credits.
- `prepare_for_dma()` temporarily accepted a `credits` argument.
- `commit_one()` committed one submitted DMA credit at a time.

## Why It Might Help

`prepare_for_dma()` is not just a trivial call. Even on the already-populated fast
path it still:

- acquires/releases the staging CAS gate
- checks K/V staging allocation
- checks `populated`
- increments `dma_inflight`
- constructs the rollback guard

If a GOF fans out to multiple target shards, doing this inside the shard loop repeats
that staging-prep overhead per target shard even though staging is GOF-level state,
not shard-level state.

The prepare-once fanout shape pays the staging gate and populated/allocation checks
once per GOF/layer dispatch, then submits per-shard DMA descriptors.

## Why It Was Backed Out

The experiment adds complexity to the `dma_inflight` ownership model: one guard owns
multiple credits and transfers them one at a time to tracker entries. That may be a
reasonable optimization, but it should be measured separately rather than mixed into
the baseline review cleanup.

After backing it out, the workspace patch was compared byte-for-byte with the perf-run
tracked diff:

```text
/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes/candidate_tracked_diff.patch
```

The matching backed-out snapshot is:

```text
/scratch/jhan/workspace/story2814/PR2906/before_gof_rodeo_split.patch
```

Both had SHA-256:

```text
7d68ef1473274aecaa5ef45294d6ba87248e4ca640a81759c9c28800836ca35c
```

## Status

Backed out. Current workspace is at the pre-prepare-once-fanout state.
