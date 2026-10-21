# Before GOF Rodeo Split Snapshot

Patch:

```text
/scratch/jhan/workspace/story2814/PR2906/before_gof_rodeo_split.patch
```

This snapshot was taken after backing out the experimental `gof_rodeo_impl()`
prepare-once fanout split.

It was compared byte-for-byte against the tracked diff used for the perf run:

```text
/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes/candidate_tracked_diff.patch
```

Both files had the same SHA-256:

```text
7d68ef1473274aecaa5ef45294d6ba87248e4ca640a81759c9c28800836ca35c
```

Related perf notes:

```text
/scratch/jhan/workspace/story2814/compare_perf/runs/20260609_f5ea3148_dirty_vs_parent/notes
```
