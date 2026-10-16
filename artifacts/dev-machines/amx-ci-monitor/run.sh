#!/bin/sh
set -eu
export CODEX_HOME=/home/jhan/codex-home-claude-agentsrv
export PATH=/home/jhan/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /home/jhan/workspace/random/amx-ci-monitor
exec /usr/bin/python3 check.py "$@"
