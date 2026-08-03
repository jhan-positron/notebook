# Autonomy analysis and implementation recommendation

Date checked: 2026-08-03T02:31:01Z
Author: Codex review
Scope: `review/tron-perf-fluctuation/RUNBOOK.md`, its approval chain, the rendered command
layer, and Claude Code permission configuration.

This is an implementation brief for Claude. It is not itself a live-run approval record and
does not replace any hash-pinned gate record.

## Executive conclusion

The approved normal path can be made unattended, but changing `RUNBOOK.md` alone cannot do
that. Two independent gates must both pass:

```text
RUNBOOK + approval records -> campaign action is authorized
Claude/Codex runtime policy -> tool call may execute
Both pass                 -> unattended normal path
Safety failure            -> abort, restore, preserve evidence, report
```

The correct target is **autonomous success-path execution with fail-closed unattended aborts**.
It is not unconditional autonomy. A foreign process, hash mismatch, expired approval,
restoration failure, quarantined lock, semantic mismatch, or missing third-party card consent
must still stop the campaign. The unattended behavior at those boundaries is: abort once,
restore when applicable, quarantine when required, preserve evidence, report asynchronously,
and stop. It is never to bypass the guard or wait while the DUT remains half-mutated.

Do not edit the pinned `RUNBOOK.md` in place during an active campaign. Its current SHA-256 is
`42ea284a89d0f8b7fc646292c1a0aeda531e9cba0b7e198041ebec993b850d36`, and the full or shortened
hash is embedded in 23 dependent files. Use the staged approach in this document.

## Measured causes of Claude's permission prompts

### 1. The project-local `autoMode` block is ignored

The Claude Desktop session record identifies Claude Code `2.1.219` and shows that the session
was in Auto mode. Claude Code 2.1.207 and later do not read `autoMode` from
`.claude/settings.json` or `.claude/settings.local.json`. The current block in
`.claude/settings.local.json` therefore does not reach the Auto-mode classifier. Project-level
`permissions.allow` rules are still read.

Official reference:
https://code.claude.com/docs/en/auto-mode-config#where-the-classifier-reads-configuration

`autoMode` must be placed in one of:

- user settings: `C:\Users\jibin\.claude\settings.json`;
- managed settings; or
- a file supplied with `--settings` for a CLI/SDK invocation.

The current user settings contain only:

```json
{
  "autoUpdatesChannel": "latest",
  "skipWorkflowUsageWarning": true
}
```

They do not select `permissions.defaultMode: "auto"`. A desktop mode choice can be remembered
per folder, but the portable default is absent.

### 2. The denied calls were compound commands

Observed denied shapes included:

- `sha256sum ... | tee ...`;
- `D=...; ssh ...` and `S=...; scp ...`;
- `cd ... && sha256sum ... && scp ...`;
- token minting as `mkdir && head | od | tr > file`;
- local heredoc writes with `cat >` or `cat >>`.

Claude Code splits `&&`, `||`, `;`, pipes, background operators, and newlines into separate
subcommands. Every subcommand must independently match an allow rule. An allow rule also does
not match through an arbitrary leading shell-variable assignment.

Official reference:
https://code.claude.com/docs/en/permissions#compound-commands

Therefore `Bash(sha256sum *)` does not authorize `tee`, and `Bash(ssh *)` does not authorize an
arbitrary leading assignment or unrelated local write.

### 3. Three rendered command-layer installers exceed the parser limit

Measured command text in `prelive/10.1-command-layer.md`:

- C1a `approval_tool.py` installer, around line 921: 10,590 characters;
- `preflight_assemble.py` installer, around line 1260: 10,230 characters;
- `manifest_assemble.py` installer, around line 1731: 12,917 characters.

Claude Code documents that commands longer than 10,000 characters always prompt because its
command analyzer does not parse them. These are deterministic unattended-execution failures,
independent of the prose delegation.

Official reference:
https://code.claude.com/docs/en/permissions#read-only-commands

Several smaller inline SSH heredoc installers are also classifier-sensitive remote writes.
All outer SSH heredoc installers should be removed, not only the three above the hard limit.

### 4. RUNBOOK v7 contains obsolete status and authority statements

`RUNBOOK.md` still says:

- live work is `NO-GO` except read-only inventory and drafting;
- none of the Section 10 artifacts exists;
- each live gate requires a new recorded go-ahead from the owner;
- heavy analysis must never run on `delphi-3bda`, despite later approved CPU/filer-only use;
- the only write roots are run/analysis roots and new review documents.

The current `prelive/` and `approvals/` trees contradict those snapshot statements. An agent
following v7 literally can correctly conclude it must ask again or stop, even when a later
standing delegation and gate record exist.

The runbook also lacks a truthful terminal state for a preparation/build attempt that stops
before acquiring the canonical lock and before mutating the DUT. Requiring `RESTORED` and
`LOCK_RELEASED` in that case invites false markers. This defect already caused a halted Gate-2
build directory to block the conflict scan.

### 5. A runbook cannot override the runtime permission engine

Claude Code permissions are enforced by the harness, not by the model. User messages,
`CLAUDE.md`, RUNBOOK prose, and approval records influence what Claude attempts, but actual
tool access comes from permission rules, permission mode, sandbox settings, and the Auto-mode
classifier.

Official reference:
https://code.claude.com/docs/en/permissions

Codex has a separate sandbox and approval layer. Claude settings do not configure Codex.

## P0 provenance defect to repair before a new live launch

Measured on disk:

- Current `STANDING_DELEGATION-ADDENDUM-20260802T175500Z.md` SHA-256:
  `6c58090fdbf116ab1c61d6ce30631ace0e2d5f8b6484c7af3c42990a81db3d57`.
- Its sidecar and downstream records cite:
  `e13da187837390096109ee7850a91fefe7e216a05c58dbcebdce3fd2bd1234db`.
- Removing only the later 360-character “Reaffirmed ...” paragraph from the current text
  reproduces the sidecar hash exactly. This proves that the file changed after the sidecar was
  minted; it does not establish why.
- Eleven files currently cite the stale `e13da187...` identity.
- `STANDING_DELEGATION-ADDENDUM-2-20260802T210000Z.md` has a valid matching hash:
  `95ff24c6870137add2145c9927924c294b2f5471e01549f3787dd3cbcbc85e3a`.

Do not silently delete the later paragraph or rewrite historical approval records to make the
old hash appear valid. Use a transparent correction chain:

1. Preserve the mismatched file and sidecar as evidence.
2. Copy the current addendum bytes to a new, explicitly versioned addendum filename and hash
   those bytes, or create a dedicated provenance-correction record that pins both identities.
3. Record that the old sidecar identifies the pre-reaffirmation bytes and that the current
   file hashes to `6c58090f...`.
4. Mark affected live records as superseded; do not mutate them in place.
5. New live records must cite the corrected addendum identity, the valid Addendum 2 identity,
   and the correction record.

## Recommended implementation sequence

### Phase 0 — do not disturb an already-running state machine

This review does not authorize interrupting a currently running build or live run solely to
apply documentation changes. If a run is active, its existing abort/restore/lock state machine
governs. Do not start a new live run from this brief until the provenance defect above is
resolved and new records validate.

### Phase 1 — repair and verify the permission configuration

Merge the existing project `autoMode` content into
`C:\Users\jibin\.claude\settings.json`; do not replace the two existing user-setting keys.
A suitable scoped structure is:

```json
{
  "autoUpdatesChannel": "latest",
  "skipWorkflowUsageWarning": true,
  "permissions": {
    "defaultMode": "auto"
  },
  "autoMode": {
    "environment": [
      "$defaults",
      "Organization and primary use: jhan's private hardware-performance lab; Claude runs hash-pinned tron experiments and analysis, not production deployment.",
      "Trusted lab hosts for this campaign: delphi-3bda, delphi-3af6, and jhan@andoria-06. Use one-shot non-interactive SSH/SCP only; these hosts are inside the campaign trust boundary.",
      "Campaign governance and mutable project scope: C:/Users/jibin/Documents/claude_debug_3bda_flat_freq/review/tron-perf-fluctuation/prelive/** and approvals/**. Signed consensus files and from-claude/** and from-codex/** remain read-only.",
      "Remote mutable campaign scope on Delphi: hash-addressed staging under /scratch/jhan/approvals/, analysis under /scratch/jhan/analysis/, non-locking builds under /scratch/jhan/builds/, approved live run roots under /scratch/jhan/gate*/, and new private source worktrees explicitly named by an approval record. /var/tmp/jhan/ef-inv/tron-29924aa8 and its frozen binary are immutable evidence.",
      "An active, unexpired, hash-valid approval record is the reservation and bounds every write, service lifecycle action, build, and benchmark launch. The agent issues or renews records under the recorded standing delegation and logs each decision."
    ],
    "allow": [
      "$defaults",
      "For this tron campaign, one-shot SSH/SCP reads and bounded writes to delphi-3bda, delphi-3af6, and jhan@andoria-06 are allowed when the exact host, path, action, hashes, and time window are covered by a valid non-superseded approval record.",
      "For this tron campaign, creating and writing hash-pinned staged tools, approval records, analysis roots, non-locking build roots, approved run roots, and truthful outcome markers in the named mutable scopes is routine campaign work.",
      "For this tron campaign, acquiring and releasing the canonical lock, capturing the manifest, stopping and restoring rinzler@0..3, stopping CI only when the active record authorizes it, launching the approved benchmark kit, and signaling only the revalidated owned process group are allowed parts of the reviewed success and abort state machines.",
      "For Gate 2, instrumenting and compiling tron in a new private worktree is allowed when source_write_authorized is true and the active record pins the base commit, patch, command layer, toolchain inputs, and build window. The frozen tree and binary remain untouched.",
      "Editing and versioning the campaign's own documents under prelive/** and issuing new or superseding hash-pinned records under approvals/** are allowed under the owner's recorded delegation. Historical records are never silently rewritten."
    ],
    "hard_deny": [
      "$defaults",
      "For the tron campaign, never modify the frozen artifacts under /var/tmp/jhan/ef-inv/tron-29924aa8 or their checksum evidence.",
      "For the tron campaign, never kill by user, name, substring, or unvalidated PID; only a revalidated owned PGID may be signaled.",
      "For the tron campaign, never auto-steal a stale lock, clear a quarantined lock without the runbook predicate, fabricate RESTORED or LOCK_RELEASED markers, disable CI timers, bypass a failed hash/statistical/semantic/restoration gate, or use andoria-06 cards without the required external ownership confirmation."
    ]
  }
}
```

Notes:

- These are natural-language Auto-mode rules, not Bash patterns.
- Keep `"$defaults"` in every customized rule array so built-in safety rules remain active.
- Do not set `bypassPermissions` and do not add blanket `Bash` or `Bash(*)`. The lab hosts and
  shared NFS make bypass mode an inappropriate control.
- The project-local `.claude/settings.local.json` should keep only scoped tool rules. Remove its
  ineffective `autoMode` block after the user-level configuration is verified, so future
  readers do not mistake it for active policy.
- Narrow `Bash(ssh *)` and `Bash(scp *)` to the three named hosts after §10.1 uses one canonical
  option order. Avoid many equivalent `ConnectTimeout` and `BatchMode` spellings.

After saving settings:

1. Run `claude auto-mode config` and verify that every custom environment, allow, and hard-deny
   entry appears in the effective JSON.
2. Confirm `/status` reports Auto mode.
3. Start a fresh main session and fresh subagents. Do not resume pre-change subagents for the
   live chain; observed old subagents retained stale permission behavior.

### Phase 2 — add a scoped execution overlay without changing RUNBOOK v7

Create a new hash-pinned execution/autonomy overlay in `review/tron-perf-fluctuation/`. It
should explicitly state that v7's dated status paragraphs are historical snapshots while all
scientific and safety predicates remain normative. Point a project `CLAUDE.md` to the overlay,
the corrected delegation chain, and the latest valid status record.

The central clause should be:

> Authorization is record-based, not conversational. When current bytes pass every required
> predicate and a valid standing delegation covers the action, the implementation agent issues
> or renews the hash-bound approval record and proceeds without asking the owner again. A user
> prompt is not an additional gate. Conditional safety failures terminate the run according to
> the abort/restoration state machine; they do not authorize bypassing a guard.

The overlay must also say:

- “STOP POINT” means an artifact/data predicate, not a conversational checkpoint.
- The agent may decide defaults, obtain delegated adversarial review, issue the record, and
  proceed when all predicates pass.
- On a failure predicate, the agent aborts/restores/reports and stops rather than requesting
  permission while holding resources.
- Gate 4's other-engineer card confirmation remains a real external prerequisite; it cannot be
  manufactured by owner delegation.

Hash the overlay and include it in every new approval record that relies on this operational
interpretation.

### Phase 3 — normalize the rendered command layer

Revise §10.1 and its generated tools with these mandatory rules:

1. One external action per Bash tool call.
2. The command begins directly with the permitted executable. No arbitrary leading variable
   assignment.
3. No `cd &&`, `tee`, local output redirection, or local heredoc in an execution call.
4. Use the file-edit tool for local governed files, then hash them with one direct
   `sha256sum` call.
5. Materialize every remote script/tool as a local, reviewable, hash-pinned file. Transfer it
   using one direct `scp` call. Verify it using one short `ssh ... sha256sum` call. Invoke it
   using one short `ssh` call.
6. No outer SSH heredoc installer. No rendered command may exceed 10,000 characters; target
   less than 4,000 characters for readable classifier input.
7. Use one canonical SSH form everywhere, for example:
   `ssh -o BatchMode=yes -o ConnectTimeout=20 <host> '<visible one-shot command>'`.
8. Use a small hash-pinned local token-mint helper. It writes the token atomically without
   printing it into the transcript. Do not implement C0 as a compound shell pipeline.
9. Use staged `lock_release.sh`, which performs targeted `rm -f` followed by validated `rmdir`.
   Delete the rendered `rm -rf "$LOCKDIR"` form.
10. Remote environment reads must filter on the remote host before output; never copy a raw
    `/proc/<pid>/environ` into the transcript.

The approval record must pin every materialized helper's path, byte count, and SHA-256. This
turns the permission boundary into the same byte boundary used by the campaign.

### Phase 4 — repair lifecycle and namespace semantics

RUNBOOK/§10.1 must distinguish three modes:

1. **Read-only/analysis:** no DUT mutation; writes only to the approved analysis root.
2. **Preparation/build:** new worktree and compilation only; no canonical DUT lock, cards,
   serving disruption, or live-run markers. Store under `/scratch/jhan/builds/...` or another
   explicit non-locking namespace.
3. **Live:** lock-holding benchmark/intervention work under the live-run namespace.

Recommended lifecycle rule:

- Perform pre-lock preparation in a preflight/build namespace.
- Create or promote the live run directory only after successful canonical-lock acquisition.
- A pre-lock failure ends truthfully as `ABORTED_PRELOCK + DUT_UNCHANGED + LOCK_NOT_ACQUIRED`,
  or remains a terminal record in the non-locking namespace.
- Never write `RESTORED` if nothing was restored and never write `LOCK_RELEASED` if no lock was
  acquired.
- The live conflict scan examines only the lock-holding namespace.

This closes Amendment Queue A1 without bookkeeping fiction.

### Phase 5 — produce RUNBOOK v8 after active work stops

RUNBOOK v8 should make these changes:

- Replace mutable campaign-status prose with: “This runbook defines predicates. Current status
  is determined by the latest valid, non-superseded, unexpired approval and status records.”
- Replace “recorded go-ahead from the owner” with “a valid per-gate approval record whose
  approver seat is satisfied by a fresh owner decision or a valid standing delegation.”
- State explicitly that delegated record issuance does not require another conversation.
- Add the preparation/build mode and truthful pre-lock terminal state.
- Enumerate exact mutable local and remote roots; retain signed/frozen evidence as read-only.
- Make the observed manifest/preflight authoritative for CI state rather than the dated
  calendar snapshot.
- Let the current approved §10.1 analysis-host record govern CPU/filer analysis placement;
  retain the no-overlap-with-measurement and no-FPGA constraints.
- Define deterministic `Insufficient data`/`Inconclusive` behavior for unavailable ring fields
  and Gate-3 branch ties, so those cases do not become conversational questions.
- Preserve owner-only or external boundaries: quarantine recovery, foreign processes,
  restoration failure, consensus changes, and Gate-4 card ownership.

Because the v7 hash appears in 23 files, v8 activation requires:

1. a new runbook review/signoff and SHA-256;
2. propagation of the v8 identity through shared conventions and every dependent §10 artifact;
3. updated lock/report schemas and analysis constants that embed the runbook hash;
4. a new §10.1 bootstrap record;
5. superseding live approval records; and
6. full hash/conformance verification before any launch.

Do not mechanically replace `42ea284a...` without reviewing each dependent use.

## Acceptance criteria

The autonomy change is complete only when all of the following are measured:

- `claude auto-mode config` shows the intended user-level campaign rules.
- A fresh desktop session and fresh subagents report Auto mode.
- The historical mismatched addendum is preserved and a valid correction/supersession chain
  exists.
- Every active approval record passes its own detached hash check and cites valid delegation,
  bootstrap, command-layer, and overlay identities.
- No rendered Bash/PowerShell command exceeds 10,000 characters; target maximum is under 4,000.
- No execution command begins with an arbitrary assignment or combines unrelated writes with
  `&&`, `;`, a pipe, or a heredoc.
- All remote tools are materialized, transferred, and hash-verified before invocation.
- Dry-run/rehearsal of the complete successful Gate-1.5 and Gate-2 paths produces zero
  permission prompts in a fresh session.
- Rehearsal of each safety failure produces the declared abort/restoration/quarantine outcome
  without a conversational approval request and without false terminal markers.
- Frozen artifacts remain byte-identical.
- No tests, assertions, hash gates, statistical gates, semantic gates, lock predicates, or
  restoration checks were weakened to obtain autonomy.
- “Tests pass” is reported only if none were skipped; otherwise list every skipped check and
  its blocking measurement.

## Recommendation to the implementing Claude agent

Use this order:

1. Audit whether a run is currently active; do not interrupt it merely to edit governance.
2. Repair the delegation provenance with a transparent superseding chain.
3. Prepare and verify the merged user-level Auto-mode configuration; obtain the one protected
   settings-file write if the harness requires it.
4. Start a fresh session and fresh subagents.
5. Create and hash the scoped execution/autonomy overlay plus project guidance.
6. Normalize §10.1 and materialize the long inline tools.
7. Review, hash, bootstrap, and issue new gate records.
8. Rehearse every success and failure path.
9. Launch only after all acceptance criteria pass.
10. Consolidate the overlay into fully re-pinned RUNBOOK v8 after active campaign work stops.

Do not claim that RUNBOOK prose overrides Claude Code or Codex permissions. Do not use
`bypassPermissions`. Do not silently repair history. Do not turn a fail-closed safety condition
into an allow rule. The desired outcome is unattended execution of already-approved, validated
actions—not removal of the campaign's safety boundaries.
