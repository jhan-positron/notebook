#!/usr/bin/env bash
# gen_s1.sh: builds the page from the session 1 folders. For session 2, add: --session s2 <folders...>
R=/home/jhan/workspace/titan/cache-perf/crb/results
H=$(dirname "$(realpath "$0")")
PYTHONDONTWRITEBYTECODE=1 python3 $H/make_q1_html.py --session s1 $R/B7-20261113T232859Z $R/B10a-20261113T235919Z $R/B10b-20261114T003359Z $R/B8-20261114T010839Z $R/B5-20261114T011723Z $R/B9-20261114T012105Z $R/B1-20261114T012315Z $R/B4-20261114T014024Z $R/B6-20261114T014825Z $R/B2-20261114T015517Z $R/B3-20261114T020808Z $R/C1-20261114T022058Z $R/C2-20261114T022500Z $R/C3-20261114T022708Z "$@" -o $H/partB-q1-result.html
