Resolving this thread, as the approval says that it does not block the merge.

State at the head:

- Both `t_amx_numerics` rows carry `"skip_return_codes":[4]`.
- Both `t_amx_dispatch_dtype` rows still record `max_rss_mb` 8. The test now peaks at 96.75 to 99.0 MiB on a Granite Rapids host.
- I did not run `bin/slice bench --update`.

The description lists the rows under Open items. The weekly refresh (`bench-refresh.yml`) measures main on both machine classes.
