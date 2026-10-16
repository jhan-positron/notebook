---
name: platformd-amx-sst-brief-2026-10-05
description: Brief for John Mark (platformd owner) on what platformd needs for AMX and Intel Speed Select; file location, key conclusions, and open questions as of 2026-10-05
metadata:
  type: project
---

Brief written 2026-10-05 for jhan's meeting with John Mark (platformd owner): `~/workspace/random/from-claude/platformd-amx-sst-brief-2026-10-05.md` (about 4,900 words), long research version `-long.md` (about 7,200 words), workflow script beside them. 20-agent research workflow plus two verification rounds (78 + 35 findings applied).

Key conclusions: AMX needs little from platformd (kernels ship in the deb since 2026.09.23 and self-enable; needs engine restart after package install and a per-engine TRON_AMX_DISABLE channel in instance-N.env). Speed Select needs more: derive the fast set from resource-map `tron_cores` (+ `peer_cores`) + HT siblings, verify CLOS associations after boot/provisioning (not service status), and John must decide ownership vs the Ansible role + boot service `intel-speed-select-state`. FE un-clamp still undeployed as of 2026-09-17.

**Why:** the user explicitly scoped the brief to WHAT platformd must do, not HOW, and asked that the build-option status (CMake default OFF, deb preset ON) be recorded.

**How to apply:** if asked for follow-ups from the John Mark meeting, start from the brief's section 6 (12 open questions) and the "Still owed by jhan" list. Related: [[3bda-ci-amx-shape-models-2026-09-18]], [[3bda-rinzler-takeover-harness-2026-09-15]].
