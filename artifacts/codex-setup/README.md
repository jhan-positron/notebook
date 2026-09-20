# Preserved Codex setup files

## Short version

These are mirrors of personal instruction files and setup recipes. Edit the canonical source first.


## Codex handoff preservation — 2026-09-18

Canonical files remain authoritative. This batch preserves authored documents, scripts, and compact audit results. Raw logs, source archives, binaries, and browser captures stay at their original locations.

HTML pages retain their canonical workspace evidence links. The mirrors preserve the authored pages but do not make the entire source and raw-data tree available offline. Historical installers require their recorded preconditions and paths.

| Preserved file | Canonical location | Purpose and related handoff |
|---|---|---|
| [shared-codex-skills/install-shared-skills.py](shared-codex-skills/install-shared-skills.py) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/install-shared-skills.py` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/test_shared_skills.py](shared-codex-skills/test_shared_skills.py) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/test_shared_skills.py` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/share-skills.py](shared-codex-skills/share-skills.py) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/share-skills.py` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/verify-discovery.py](shared-codex-skills/verify-discovery.py) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/verify-discovery.py` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/homes.json](shared-codex-skills/homes.json) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/homes.json` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/startup-expected-sha256](shared-codex-skills/startup-expected-sha256) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/startup-expected-sha256` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [shared-codex-skills/jibin.bashrc.positron.proposed](shared-codex-skills/jibin.bashrc.positron.proposed) | `claude-agentsrv:/home/jhan/workspace/random/shared-codex-skills/jibin.bashrc.positron.proposed` | Shared-skill installation recipe or required sibling input. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [skills/plain-english/SKILL.md](skills/plain-english/SKILL.md) | `claude-agentsrv:/home/jhan/.codex/skills/plain-english/SKILL.md` | Current shared personal skill instructions. Related: [codex_20260911_reimport-updated-plain-english-skill.md](../../handoffs/codex_20260911_reimport-updated-plain-english-skill.md). |
| [skills/cpp-coding-guide/SKILL.md](skills/cpp-coding-guide/SKILL.md) | `claude-agentsrv:/home/jhan/.codex/skills/cpp-coding-guide/SKILL.md` | Current shared personal skill instructions. Related: [codex_20260912_identify-codex-skill-equivalent.md](../../handoffs/codex_20260912_identify-codex-skill-equivalent.md). |

## Handoff preservation — 2026-09-20

Canonical means the original working copy. These files preserve the handoff-rule review and the installed skill wrapper. The historical installation did not record an exact upstream commit. The license is the full notice recovered from the installation transcript.

Root mappings: `handoff-prompt-20260919/` maps to `claude-agentsrv:/home/jhan/tmp/handoff-prompt-2026-09-19/`, except the explicit `review.md` mapping below. `skills/grill-with-docs/` maps to `claude-agentsrv:/home/jhan/codex-home-claude-agentsrv/skills/grill-with-docs/`, except the repository-primary license snapshot. The installed skill remains in its operational location.

- [`handoff-prompt-20260919/review.md`](handoff-prompt-20260919/review.md) — Review of preservation rules, including the later Claude response.
  - Canonical: `claude-agentsrv:/home/jhan/tmp/codex-review-claude-handoff-prompt-2026-09-19.md`
  - Related handoff: [codex_20260920_review-claude-handoff-plan.md](../../handoffs/codex_20260920_review-claude-handoff-plan.md)
  - generator: none (authored review)
  - input: none
  - input built by: none
  - sources: preserved failure analysis, comparison generator, and input table under `artifacts/intel-amx/`; temporary Git fixture left behind (missing on 2026-09-20). Exact paths and sizes are in the inventory.
  - regenerate: none
  - regenerate unverified (authored review; no generator)
  - inventory: [`review.md.lineage.md`](handoff-prompt-20260919/review.md.lineage.md)

- [`handoff-prompt-20260919/CHANGES.md`](handoff-prompt-20260919/CHANGES.md) — Prompt change rationale and adoption history.
  - Canonical: `claude-agentsrv:/home/jhan/tmp/handoff-prompt-2026-09-19/CHANGES.md`
  - Related handoff: [codex_20260920_review-claude-handoff-plan.md](../../handoffs/codex_20260920_review-claude-handoff-plan.md)

- [`handoff-prompt-20260919/VERIFY.md`](handoff-prompt-20260919/VERIFY.md) — Verification findings and accepted fixes.
  - Canonical: `claude-agentsrv:/home/jhan/tmp/handoff-prompt-2026-09-19/VERIFY.md`
  - Related handoff: [codex_20260920_review-claude-handoff-plan.md](../../handoffs/codex_20260920_review-claude-handoff-plan.md)

- [`handoff-prompt-20260919/review.md.lineage.md`](handoff-prompt-20260919/review.md.lineage.md) — Exact evidence inventory and explicit missing temporary-fixture limitation.
  - Canonical: `repository-primary authored lineage inventory`
  - Related handoff: [codex_20260920_review-claude-handoff-plan.md](../../handoffs/codex_20260920_review-claude-handoff-plan.md)

- [`skills/grill-with-docs/SKILL.md`](skills/grill-with-docs/SKILL.md) — installed third-party skill wrapper.
  - Canonical: `claude-agentsrv:/home/jhan/codex-home-claude-agentsrv/skills/grill-with-docs/SKILL.md`
  - Related handoff: [codex_20260919_install-grill-with-docs-skill.md](../../handoffs/codex_20260919_install-grill-with-docs-skill.md)

- [`skills/grill-with-docs/agents/openai.yaml`](skills/grill-with-docs/agents/openai.yaml) — required sibling invocation/display metadata.
  - Canonical: `claude-agentsrv:/home/jhan/codex-home-claude-agentsrv/skills/grill-with-docs/agents/openai.yaml`
  - Related handoff: [codex_20260919_install-grill-with-docs-skill.md](../../handoffs/codex_20260919_install-grill-with-docs-skill.md)

- [`skills/grill-with-docs/LICENSE`](skills/grill-with-docs/LICENSE) — required upstream copyright and permission notice.
  - Canonical: `repository-primary snapshot of the complete upstream license recorded in the installation transcript, line 50`
  - Related handoff: [codex_20260919_install-grill-with-docs-skill.md](../../handoffs/codex_20260919_install-grill-with-docs-skill.md)

Left behind: the temporary Git fixture used in the review was deleted after the check. Its outcome is recorded in the review and transcript. It cannot be restored as raw test output. The adopted prompt and its prior revision are already preserved in Git history.
