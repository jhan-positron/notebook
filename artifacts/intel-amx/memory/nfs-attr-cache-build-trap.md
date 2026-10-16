---
name: nfs-attr-cache-build-trap
description: "editing build inputs on alpha and building on 3bda within seconds compiles STALE file content while ninja still rebuilds; verify content on the build host before building (hit 2026-08-31, fence campaign smoke failure)"
metadata:
  type: feedback
---

Hit 2026-08-31 during the fence campaign: patched a generated header on alpha over NFS, started
the 3bda rebuild ~30 s later. ninja saw the new mtime and recompiled 70 objects, but the compiler
read the PRE-EDIT page content from 3bda's NFS attribute/page cache - the binary silently lacked
the edit. A grep on 3bda minutes later showed the new content (cache refreshed), so post-build
checks lied. A second rebuild minutes later picked the edit up.

**Why:** NFS close-to-open consistency only guarantees fresh content when the reader revalidates
at open; within the attribute-cache window a client that already cached the file can serve stale
pages while stat shows the new mtime. Symptom pattern: rebuild triggers, binary behaves as if
unpatched, later inspection of the file looks correct.

**How to apply:** after editing any build input cross-host, BEFORE building: run the content
check ON THE BUILD HOST and require the edit to be visible (grep for the new text), or make the
edit on the build host itself; add a runtime verification of the edit's effect (the fence
campaign's smoke gate caught this - keep such gates). Related: [[claude-box-tron-build-env]],
[[delphi-3bda-hardware]].
