# Change under review (local, not yet a pull request)

Repository: positron-ai/tron. Base revision: ddf843ad97. The change is the uncommitted working-tree diff of the worktree named in the task.

Author's description:

> hwalloc: test that the shadow profile drops a freed site
>
> `render_profile` lists the live allocation sites of the hardware allocator when the build option
> `HBM_ALLOC_SHADOW` is on. The existing test covers one live site. This change adds a case with two sites,
> frees one, and requires that the profile lists only the remaining one.
>
> Verification: built with `cmake --preset native -DHBM_ALLOC_SHADOW=ON` on my machine;
> `gen/t_hwalloc "[shadow]"` passes 2 test cases.
