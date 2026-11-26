Here's the one open point from my review of #5022 as code instead of a comment. If you like it, take the two commits: cherry-pick them, or fast-forward your branch to this one. They sit on your head `ddf843ad97`.

## What changes

- **`t_amx_dispatch_dtype` runs its real cases wherever the tests are built.** It passes `TRON_AMX_DISPATCH` itself, the way `t_page_share_counters` passes its own define. With the option off the test was one placeholder case; now its dispatch checks run there too.
- **Nothing else sees the option.** The model tests of the required lane are unchanged, which was your reason for keeping the flag out of the Nix build. The option only changes code inside the `self_attention<model>` template, and no other translation unit in the test binary instantiates that template for the test's models.
- **The placeholder case is gone** (second commit). With the guard in place, a registration that loses the define compiles to the placeholder and passes; without the guard the test fails instead. You can drop this commit, at that cost.
- **The CMake comments and `README.ci.md` say where the test runs.**

## Where my review was wrong

- The registration line I suggested for `t_amx_numerics` (`LABELS "fake;skip_return_code_4"` through `add_catch_test`) does not configure. What you did instead is right.

## Heads-up

- **Your description goes stale in one place.** The Verification row for the default CI build says the AMX checks are compiled out. That no longer holds for this test.
- **The benchmark rows for `t_amx_dispatch_dtype` record 8 MB.** With its real cases the test peaks near 99 MiB by your measurement. `t/AGENTS.md` asks for a `bin/slice bench --update` after a change like this. I did not run it, because it needs a run on each machine class.
- A real-AMX run in required CI (your TODO, #3997) is a separate thing and still open.

## Tested

In the Nix sandbox, in a build with the option off, at this branch's tip: the test passes 30,747 assertions, where before it was one placeholder assertion. Eight one-line faults in the dispatch code each make it fail there, and so does removing the define. It also passes with the option on, and the first commit builds and passes on its own. The sandbox build is not the full CI lane (it leaves out the lane's model flags), and draft CI runs only lint and contract checks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
