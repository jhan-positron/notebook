## Short version: purpose

`fetch.sh` copies result folders from CRB, the Arm server under test, to the agent server in one `ssh` login. The login first checks the marker file and then packs the named folders with `tar`, and a local `tar` unpacks them into the folder `crb/results/`. At the end the script prints the exit statuses of the two commands.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Archive**: one stream of data that the tool `tar` makes from files and folders. A second `tar` turns it into files and folders again.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the test plan of 2026-11-13.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Set the folder on the agent server that gets the copies ({L3}).
2. Keep the text of the marker check in `M` ({L4}).
3. Log in to CRB once. The remote command checks the marker file and packs the named result folders into an archive. The archive comes back through `ssh`, and a local `tar` unpacks it ({L5}).
4. Print the exit statuses of `ssh` and of the local `tar` ({L6}).

## Behavior a reader must know

- On CRB the script only reads: the remote `tar` writes the archive to its output and changes no file there.
- On the agent server `tar` replaces a file that has the same path as a file of the archive.
- The script has no `set -e`. Its own exit status is the status of the last `echo`. A failed copy shows only in the printed line: any number other than 0 after `status` ({L6}).
- The marker file is checked once, at the start of the login. The copy is not stopped when the marker file appears later.
- The copy runs inside an `ssh` login for a reason that the handoff note gives: a copy with `scp` is a login that cannot check the marker file first.
- The script makes no Slack check. The caller must do it before the call, as for every login.
- The folder names of the call are names below `~/cache-perf/results` on CRB. The same names appear below the folder `R`.
