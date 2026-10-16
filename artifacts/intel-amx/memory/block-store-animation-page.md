---
name: block-store-animation-page
description: "2026-09-17 companion page to the store-remedies report: VNNI K block store played step by step (status/block-store-animation.html, artifact Mr7Vu2qJcA1uVdxP6kFiUh), generator + compiled ground truth in exec/block-store-animation/"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a126579-5079-48cd-9016-3bd8450c6038
  modified: 2026-09-17T01:23:28.480Z
---

Page: VNNIed-K-in-place/status/block-store-animation.html = artifact
https://claude.ai/artifact/Mr7Vu2qJcA1uVdxP6kFiUh (favicon film frames). Generator
VNNIed-K-in-place/exec/block-store-animation/gen_page.py; positions come from
gt.cpp (the real k_vnni::store_block run on mock rows, built by build-gt.sh with
a bf16 shim because g++ 11 on claude-box lacks __bf16; nix is NOT at
~/.nix-profile/bin/nix on claude-box any more). The report generator
~/workspace/intel-AMX/exec/vnnik2-20260915/gen_report.py got sub-section 3.1.2
pointing at the page; report artifact E8czhhjwBmC2qqPvVKPthD republished (v5).

Facts jhan asked about (2026-09-16): the 4 dim steps of one K row are ONE
contiguous 256-byte row (Figure 3.1a stacked them); store order = s0 lines 0-15
(stores 1-16, plane bytes 1024-2047 for block c1), then s1 (5120..), s2 (9216..),
s3 (13312..); token 21 = column 5 = +20..+23 in each of its 64 lines.

Mock value scheme: token T, dim d = (T - 21) + 0.11 + 0.01 d (token axis steps
1.00, dim axis 0.01); bf16 rounds the larger tokens' neighbours together, page
says so. Cache model on the page is labelled schematic; RFO-avoidance on
full-line stores is an open, unmeasured question.

**Why:** jhan wanted real numbers, row/column positions, cache+DRAM and the
save order instead of colour coding; the page is the reference for that.
**How to apply:** regenerate with gen_page.py after code changes; rerun
build-gt.sh first if k_vnni.hpp changes. Related: [[vnnied-k-in-place-project]],
[[artifact-utf8-mojibake-trap]] (page is pure ASCII by assertion).

Review rounds (2026-09-17): 3 workflow rounds (104 + 55 + 45 agents); round 1
confirmed 48 findings, round 2 26, round 3 21, all wording/layout/consistency,
zero number or order errors. FINAL = revision 4 (artifact version 4). Generator
revisions kept as gen_page.py.draft1 / .rev2 / .rev3; REV constant in gen_page.py. Rules
learned for such pages: define cell/panel line dp/plane line L/item vs token;
never "arm" (say configuration/binary); label cache-behaviour statements as
model or hypothesis; store ORDER is program order of the loops, a final-state
check cannot observe it; a fixed-width "overview" strip must be computed with
gaps + padding + borders (use a fluid flex strip instead).
