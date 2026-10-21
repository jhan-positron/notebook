# PR2906 Note: Complete GOF That Was Never Transferred

Mike's review comment was on the `backfill_shard()` comment describing GOFs whose
rodeo path bailed with no live shards:

> I wonder if we really need to worry about the case where we have a complete gof
> that was never transferred that isn't a newly completed one. Maybe we should
> track a count of that case.

Our interpretation is that the sentence is missing an "and". The intended reading
is:

> I wonder if we really need to worry about the case where we have a complete GOF
> which was never transferred, and it isn't a newly completed one. Maybe we should
> track a count of that case.

In other words, Mike is distinguishing the normal "newly completed" GOF rodeo path
from an older/historical complete GOF that backfill later discovers.

## Cases

### Newly Completed GOF

This is the normal rodeo trigger:

```cpp
save_count transitions from 7 to 8
gof_rodeo_impl() runs
if live shards need the GOF, it prepares and submits DMA
```

This case is not the concern.

### Complete But Never Transferred, Not Newly Completed

This is the case Mike is questioning:

```cpp
save_count already == 2 * gof_tokens
gof_rodeo_impl() previously bailed, for example because there were no live shards
no DMA was submitted at that time
later, backfill_shard() sees the complete GOF and transfers it
```

The current code supports this conservatively. `backfill_shard()` checks
`save_count >= 2 * gof_tokens`, then calls `prepare_for_dma()`, which can lazily
populate the GOF from retained `page_info` and submit the DMA.

## Why `populated` Is Not Enough For The Count

`g->populated == false` does not uniquely mean "never transferred".

It can mean either:

1. The GOF was complete but never populated/transferred.
2. The GOF was transferred earlier, then staging was evicted and `populated` was
   reset to false.

So a counter for Mike's case should track first DMA submission, not just
repopulation.

## Counter Sketch

Add a GOF-level bit:

```cpp
struct gof {
  ...
  std::atomic<bool> dma_submitted_once{false};

  bool mark_dma_submitted_once() noexcept {
    return !dma_submitted_once.exchange(true, std::memory_order_relaxed);
  }
};
```

Mark both submit paths after `xfer_gof()` submits descriptors.

In `gof_rodeo_impl()`:

```cpp
auto last_v = sh->xfer_gof(*g, gof_in_shard, layer);
(void)g->mark_dma_submitted_once();
guard.commit();
tracker.push(...);
```

In `backfill_shard()`:

```cpp
auto last_v = sh->xfer_gof(*g, gof_in_shard, layer);

if (g->mark_dma_submitted_once()) {
  gof_stats::gof_first_dma_from_backfill_total.fetch_add(
      1, std::memory_order_relaxed);
}

guard.commit();
tracker.push(...);
```

This counts exactly the interesting case: the first-ever DMA submission for that
GOF happened from backfill rather than from the newly-completed rodeo path.

Suggested counter name:

```cpp
gof_first_dma_from_backfill_total
```

Suggested FUSE path:

```text
/rinzler/stats/gof_first_dma_from_backfill_total
```

Suggested descriptor:

```text
Complete GOFs whose first DMA submission happened from backfill rather than the
newly-completed GOF rodeo path.
```

## Recommendation

Keep the conservative backfill support unless we prove this case cannot happen.
If Mike wants evidence, add the counter above as an observability follow-up.
