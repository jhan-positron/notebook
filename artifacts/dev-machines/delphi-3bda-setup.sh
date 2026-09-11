######################################################################################
# This is CI machine — cancel the shared default exported by jibin.bashrc.positron.dev
# 
## Sharing 3bda with Bill currently, so set SYSTEM_CONFIG. Need to unset it when I 
## measure perf at absolute ownership.
## unset SYSTEM_CONFIG
export SYSTEM_CONFIG="--instance 1,2"


# 2026-09-06 half-split sharing with Bill (notebook/handoffs/delphi-3bda-guard.md, fix 2):
# Bill has cards 10/13/38/3b and socket 0, we have the rest, so his activity is not
# a reason for the campaign guard (exec/lib-guard.sh other_user_active) to wait.
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
