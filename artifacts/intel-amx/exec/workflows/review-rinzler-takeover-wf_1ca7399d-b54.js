export const meta = {
  name: 'review-rinzler-takeover',
  description: 'Adversarially review the shared rinzler takeover function and the our-half wait_clear hook',
  phases: [
    { title: 'Review', detail: 'five lenses over the change, read-only' },
    { title: 'Verify', detail: 'two refuters per finding' },
  ],
}

const CONTEXT = `
You are reviewing a small change to a bash test harness that runs on the shared machine delphi-3bda.
READ-ONLY: do not modify anything under /home/jhan/workspace. You may write scratch files only under
/tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/review/ (create it).
The machine delphi-3bda is unreachable right now; do not try to ssh anywhere.

Words: "rinzler@N" = the production serving systemd units (rinzler@0..3) that the nightly System CI starts
and never stops. "lease" = /run/lock/systems-test-ci.lease, the file that says whether CI holds the machine.
"our half" = the second half of the machine (SYSTEM_CONFIG --instance 1,2) that jhan's campaigns use.

What changed (2026-09-15):
1. /home/jhan/workspace/intel-AMX/exec/lib-guard.sh gained one function, rinzler_takeover_if_idle, copied
   from the "phase 0" block of /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/campaign.sh (lines ~333-365,
   the tested "round 1 recipe"). The previous version is lib-guard.sh.bak-20260915 in the same directory;
   run: diff -u lib-guard.sh.bak-20260915 lib-guard.sh
   Intended semantics: one attempt per call, for a wait loop polling every ~120 s. Return 0 when no rinzler
   unit is active on return (nothing was up, or the stop worked); return 1 otherwise. It must fail closed:
   never run "systemctl stop" when the lease is busy, when the journal is unreadable or empty, when the last
   10 min of journal show any request line or any non-idle SYSTEM_STATS line, or when any established
   remote connection exists on the serving ports (or ss fails).
2. PENDING PATCH (not yet applied to the live file, a permission classifier blocked it):
   /tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/campaign-takeover.patch
   changes wait_clear in exec/vnnik2-20260915/campaign.sh so that, when the only blocker is
   "rinzler@N unit active", it calls rinzler_takeover_if_idle each poll and re-checks without sleeping
   after a success. The patched copy is at
   /tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/patched/exec/vnnik2-20260915/campaign.sh
   The live (unpatched) file is /home/jhan/workspace/intel-AMX/exec/vnnik2-20260915/campaign.sh.
   exec/vnnik4-20260915/verify.sh and models.sh run that campaign.sh (models.sh sources it with
   VNNIK2_FUNCTIONS_ONLY=1), so they inherit the hook.
3. Existing tests (stub-based, pass locally):
   /tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/test-takeover.sh
   /tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/test-wait-clear.sh
   A shellcheck binary is at: find /tmp/claude-0/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/scratchpad/pip -name shellcheck -type f

Report only real defects or real risks with a concrete failure scenario. Do not report style preferences.
Do not report that the original recipe's behaviour was kept when keeping it was the intent, unless the kept
behaviour is itself a defect with a concrete scenario. For each finding give file, line, severity, detail,
and a suggested fix.
`

const LENSES = [
  { key: 'bash', prompt: `${CONTEXT}
LENS: bash correctness. Check the new function and the patched wait_clear for: behaviour under "set -u"
(the campaign scripts run with set -u, not set -e); quoting; exit-code propagation through "|| true" and
"$(...)"; the "&& continue" line inside the while loop (what happens when rinzler_takeover_if_idle returns
1, when blocked's output has trailing whitespace, when why is empty); the "! rinzler_active" final line;
local variable declarations; the printf/awk/grep pipelines. Compare the function line by line with the
original block in vnnik-20260914/campaign.sh and list every semantic difference (intended or not).` },
  { key: 'safety', prompt: `${CONTEXT}
LENS: fail-closed safety. Enumerate every path that reaches "sudo -n systemctl stop rinzler@0 ...".
For each, ask: can this stop a rinzler unit that CI or a person is about to use or is using? Consider:
the lease being released and re-taken between nightly stages; the 01:40-03:45 UTC pre-CI hold (production
serving starts ~02:45 UTC, the nightly takes the lease ~03:38 UTC) and how the patched wait_clear orders
its checks (blocked() checks preci_hold first, then lease, then rinzler); a unit started less than 10 min
ago whose journal has startup lines but no SYSTEM_STATS lines yet (busy=0 and traffic=0 then); the
journalctl "--since '-10 min'" semantics; ss port list vs the ports rinzler actually serves on (check
what the repo says, e.g. grep -rn 13000 /home/jhan/workspace/intel-AMX/exec | head); the hugepage file
removal branch (could it delete a file that a live process maps?). Also consider what the whole-machine
campaign did that the new hook does not (it required the lease clear for 3 consecutive polls before its
takeover loop) and whether that matters.` },
  { key: 'integration', prompt: `${CONTEXT}
LENS: integration with the rest of exec/. About 69 scripts source lib-guard.sh
(grep -rl lib-guard.sh --include=*.sh /home/jhan/workspace/intel-AMX/exec). Check: name collisions for
rinzler_takeover_if_idle or GUARD_HUGEPAGES_DIR anywhere in exec/; whether any script defines its own
"sleep", "stat", "fuser", "sudo", "ss" wrapper that the new function would pick up; whether sourcing
lib-guard.sh still has no top-level side effects; whether the patched wait_clear interacts correctly with
take_guard (campaign_guard_acquire refuses while rinzler is active, then calls wait_clear) and with the
10-second watcher watch_run; whether exec/vnnik4-20260915/verify.sh, models.sh and chain.sh get the hook
as claimed and whether any other current our-half chain (look at the newest directories in exec/) still
only waits. Read the actual code; do not guess.` },
  { key: 'tests', prompt: `${CONTEXT}
LENS: independent test author. Do NOT read the existing test files first. Write your own stub-based tests
for rinzler_takeover_if_idle (override systemctl, sudo, stat, fuser, sleep and ci_lease_busy as bash
functions; point GUARD_HUGEPAGES_DIR at a temp dir) under the scratch review directory, trying to make the
function run "systemctl stop" when it must not, or skip the stop when it should stop, or return the wrong
code, or remove a file it must not remove. Run them with bash. Then read the existing tests and list any
case they miss. Report each failing case as a finding (file = lib-guard.sh) with the exact fixture.` },
  { key: 'prose', prompt: `${CONTEXT}
LENS: comments and log lines in plain English, per jhan's rules: define a code name or acronym at first
use inside the comment block, one claim per sentence, numbers carry units, no idioms or metaphors. Check
only the NEW comment block above rinzler_takeover_if_idle in lib-guard.sh, the new log-line texts in that
function, and the new comment lines in the patch. Report each violation with the exact phrase and a
replacement. Ignore pre-existing text.` },
]

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          detail: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
        required: ['title', 'file', 'severity', 'detail'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['findings'],
}
const VERDICT = {
  type: 'object',
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
  required: ['refuted', 'reason'],
}

const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }),
  async (rev, l) => {
    if (!rev) return { lens: l.key, findings: [], notes: 'reviewer returned nothing' }
    const kept = []
    const judged = await parallel(rev.findings.map(f => async () => {
      const votes = await parallel([0, 1].map(i => () => agent(`${CONTEXT}
You are refuter ${i + 1} of 2. A reviewer (lens "${l.key}") claims the following defect in the change.
Try hard to REFUTE it by reading the actual code and, if useful, running a bash experiment under the
scratch review directory. A claim is refuted if the failure scenario cannot happen with the code as
written, or if the claimed behaviour is exactly the intended fail-closed behaviour, or if it is a style
preference with no concrete failure. If you are uncertain, set refuted=true.
Claim title: ${f.title}
File: ${f.file} line ${f.line ?? '?'} severity ${f.severity}
Detail: ${f.detail}
Suggested fix: ${f.suggested_fix ?? '(none)'}`, { label: `verify:${l.key}:${i + 1}`, phase: 'Verify', schema: VERDICT })))
      const v = votes.filter(Boolean)
      const survives = v.length > 0 && v.filter(x => !x.refuted).length >= 2
      return { ...f, lens: l.key, survives, votes: v.map(x => x.reason) }
    }))
    return { lens: l.key, notes: rev.notes ?? '', findings: judged.filter(Boolean) }
  },
)

const all = results.filter(Boolean)
const confirmed = all.flatMap(r => r.findings.filter(f => f.survives))
const refuted = all.flatMap(r => r.findings.filter(f => !f.survives))
log(`${confirmed.length} confirmed, ${refuted.length} refuted`)
return { confirmed, refuted, notes: all.map(r => ({ lens: r.lens, notes: r.notes })) }