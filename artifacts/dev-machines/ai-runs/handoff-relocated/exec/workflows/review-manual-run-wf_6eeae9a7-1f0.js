export const meta = {
  name: 'review-manual-run',
  description: 'Test manual-run.sh with stand-in programs and review it from four angles, then verify each finding',
  phases: [
    { title: 'Test', detail: 'one agent builds a stand-in harness and runs failure scenarios, no CRB access' },
    { title: 'Review', detail: 'four reviewers, one lens each' },
    { title: 'Verify', detail: 'one skeptic per reviewer tries to refute its findings' },
  ],
}

const REPO = '/home/jhan/workspace/ai-proj/arm-crb'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const CONTEXT = `
Context. The file under review is ${REPO}/manual-run.sh (new, about 160 lines of bash). Read it in full first.
Its purpose: the user runs "./manual-run.sh" at the console of the agent server. The script reaches the shared Arm server "CRB" (jhan@192.168.2.45) by ssh and repeats the complete whole-chip read test that an agent drove on 2026-11-17: checks, then the driver go.sh (about 10 min), a copy of the results, then the control driver go2.sh (about 10 min), a copy of the results, and a table of read rates.
Decisions that the user already made (do not re-open them): (1) CRB runs the script copies that are on CRB now, checked against local.sha and go2.sha there; only the fixed boot-id line is removed by sed into go-direct.sh and go2-direct.sh, as the user's older command ${REPO}/code/manual-run/run.sh does. Nothing is copied to CRB. (2) Both parts run: go.sh, then go2.sh.
Facts you can read:
- ${SCRATCH}/crb-asrun/ : byte copies taken from CRB today. w120-7200-20261117/ holds go.sh, go2.sh, ra.sh, the spec files, local.sha, go2.sha and go-direct.sh as they are on CRB. w120-20261115/rx.sh is the as-run runner. results/ holds the driver logs of 2026-11-17 (agent run) and of 2026-11-23 (the user's own run with run.sh) and the memcheck file of 2026-11-23.
- ${REPO}/tests/2026-11-17-whole-chip-7200/ : the result folders of the agent run of 2026-11-17 (k120-T72A?-*, w120-T72[LCI]?-*) and both logs.
- The exact ssh commands of the agent run of 2026-11-17 are in ${SCRATCH}/agent-run-2026-11-17-commands.txt (session record lines 309, 313, 339, 353, 365, 377).
- Sharing rules of CRB: ${MEM}/crb-ssh-login-first-command.md, ${MEM}/crb-check-dimm-count-every-use.md, ${MEM}/crb-whole-chip-rerun-7200-2026-11-17.md, ${MEM}/crb-go-sh-remove-boot-id-todo.md. Another user (Jeremy, account positron-perf) measures on CRB in announced time windows ("blocks"); the marker file /tmp/positron-perf.RUNNING exists while he runs; no login during a block; never use CPUs 126-127; a root command needs the user's approval (the read "sudo -n dmidecode -t 17" is in the user's own run.sh).
- NOTE: the files under ${REPO}/code/w120-7200-2026-11-17/ and ${REPO}/code/w120-2026-11-15/rx.sh are NEWER texts than the ones on CRB (uncommitted changes). manual-run.sh does not use them, except the two statistics scripts stat_k120.py and stat_bwx.py.
HARD RULES for you: do NOT run ssh, scp or any command that contacts 192.168.2.45 or any other remote machine. Do NOT edit ${REPO}/manual-run.sh or any file of the repository. Write files only under the scratch folder named in your task. This machine allows 6 CPUs: start no parallel jobs.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          lines: { type: 'string', description: 'line numbers of manual-run.sh' },
          evidence: { type: 'string', description: 'the exact text or the command output that proves it' },
          failure_scenario: { type: 'string', description: 'concrete state or input, then the wrong result' },
          suggested_fix: { type: 'string' },
        },
        required: ['title', 'severity', 'lines', 'evidence', 'failure_scenario', 'suggested_fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' }, description: 'things you checked and found correct, one line each' },
  },
  required: ['findings', 'checked_ok'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          real: { type: 'boolean' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'none'] },
          reason: { type: 'string', description: 'the proof: a command you ran and its output, or the exact lines' },
          fix: { type: 'string', description: 'the smallest change that fixes it, as replacement text; empty when not real' },
        },
        required: ['title', 'real', 'severity', 'reason', 'fix'],
      },
    },
  },
  required: ['verdicts'],
}

const LENSES = [
  {
    key: 'bash',
    prompt: `Lens: bash correctness. Read manual-run.sh as an interpreter would. Check: how each remote command string is composed (the variables MARKER, CHECKS, START, PACK are joined with "; " and passed as ONE argument to ssh, so the login shell on CRB, bash 5.2, runs it with -c); quoting of T, G, FILES and DIRS inside those strings; word splitting and glob expansion on the remote side in PACK (set -- $FILES, for d in $DIRS, the string comparison of the time stamps); PIPESTATUS use after "ssh | tee" and "ssh | tar"; set -u and pipefail effects (for example grep -c that counts 0 returns status 1); the traps (EXIT, INT, TERM) and the temp file; the case on "$#:\${1:-}"; the functions count, check_ra, check_rx, check_log, tables; "cd" into DEST and relative patterns after it; ssh -n. You may run small local experiments with bash under ${SCRATCH}/review-bash/ (create it). Report only defects that give a wrong result, a wrong exit status, a lost error or a hang. Do not report style.`,
  },
  {
    key: 'fidelity',
    prompt: `Lens: is it the same run? Compare what manual-run.sh makes CRB do with (a) the ssh commands of the agent run of 2026-11-17 (the commands file named above: start of go.sh in line 313, start of go2.sh in line 365, the copies in lines 339 and 377) and (b) the user's command code/manual-run/run.sh, which ran on CRB on 2026-11-23. Check: the start command of each driver (nohup, setsid, redirections, wait, what the ssh login shell does while the driver runs); that go-direct.sh and go2-direct.sh made by the sed command are the as-run drivers minus exactly the boot-id check line (apply the sed to the copies in crb-asrun in a scratch folder and diff; compare with the go-direct.sh that is on CRB); whether go2-direct.sh still works with the line "BOOT=..." left in under set -u; the lock file both drivers use; that go2.sh waits for an idle machine by itself, so the pause between the parts does not matter; anything manual-run.sh adds on CRB during the timed parts that the agent run did not have (extra processes, extra logins, files); the order and the content of the memory check against run.sh; log file names. Also say whether anything the agent run did is missing in manual-run.sh (for example a check). Write only under ${SCRATCH}/review-fidelity/.`,
  },
  {
    key: 'safety',
    prompt: `Lens: shared machine and failure paths. Walk through every way the run can end and say what the user sees and what is left running or left behind on CRB: the Slack question answered with n or with end of input; marker file present at each of the five ssh calls; marker file appearing in the middle of go.sh or go2.sh (read the as-run go.sh, go2.sh, ra.sh, rx.sh to see what they do then); checksum mismatch; 10 memory modules; sudo asking for a password; ssh connection lost during a driver; Ctrl-C at the console during a driver and during a copy; the driver failing in the middle; the lock held by another go.sh; tar failing; a full disk on the agent server; python3 failing in the tables. For each: is the exit status the documented one (header comment of the script), is the message true and sufficient, is a login made that the rules forbid, does anything keep running on CRB without the user being told. Check also that the script never touches CPUs 126-127 and uses root only for the one dmidecode read. Write only under ${SCRATCH}/review-safety/.`,
  },
  {
    key: 'results',
    prompt: `Lens: the copy and the checks of the results. CRB holds result folders of three runs under ~/cache-perf/results (2026-11-17 agent run, 2026-11-23 user run, and soon the new run), all with the same step names. Check PACK and fetch: does the rule "start time at the end of the folder name is not before the run id" select exactly the folders of the new run, also for the go2 part (w120-T72I?-*), also when a step failed and a folder is missing, and can a folder of an older run or of the other part slip in? Check the expected counts in check_ra and check_rx (24 headers, 72 intervals, 1 rc0, 10 I rows for parts L and I, 6 I rows for part C, 3+3+4+2 folders) against the as-run scripts, the spec files and the stored data of 2026-11-17: run the same grep commands on ${REPO}/tests/2026-11-17-whole-chip-7200. Check the regular expression of the interval rows. Check the local folder name built from the run id, and what happens when two runs start on the same day. Check the tables: run the three pipelines of the function tables on the stored data of 2026-11-17 (cd into that test folder; STAT is ${REPO}/code/w120-7200-2026-11-17) and say whether every printed number is what its label says and whether the comment above the function is true (units, which kernel is which). Check that a failed table gives status 14. Write only under ${SCRATCH}/review-results/.`,
  },
]

phase('Test')
const testerP = agent(`${CONTEXT}
Your task: test manual-run.sh end to end WITHOUT CRB, with stand-in programs, and report defects.
Work only under ${SCRATCH}/harness/ (create it). Build:
1. A fake CRB home folder: cache-perf/w120-7200-20261117/ with stand-in drivers go.sh and go2.sh that hold a line with the text "boot id is not the boot checked" (so the sed has something to delete, and the stand-in must fail if that line is still present when it runs), that write a log line "go.sh pid ..." and result folders under cache-perf/results/ with fresh time stamps (copy the content of the folders of ${REPO}/tests/2026-11-17-whole-chip-7200: k120-T72A1..3, w120-T72L1..3, w120-T72C1..4 for go.sh and w120-T72I1..2 for go2.sh; name them <prefix>-<step>-<now in the form YYYYMMDDTHHMMSSZ>, each a second or more apart is not needed, equal stamps are fine), print ALLDONE and exit 0. Write matching local.sha (go.sh, ra.sh, like.spec, cfwd.spec, crev.spec) and go2.sha (go2.sh) lists. Also put OLDER result folders of the same step names (stamps of 2026-11-17 and 2026-11-23) and an older go-T72 log into the fake results folder, to test that they are not copied.
2. A fake "ssh" program, first in PATH, that ignores its options and the host argument, takes the LAST argument as the command string, rewrites the paths /tmp/positron-perf.RUNNING, /proc/meminfo and /proc/sys/kernel/random/boot_id in it to files of the harness, and runs it with: env HOME=<fake home> PATH=<fake bin>:$PATH bash -c "<string>". Provide a fake "sudo" (prints 12 lines "\\tConfigured Memory Speed: 7200 MT/s" for "sudo -n dmidecode -t 17") and fake "nohup"/"setsid" only if needed (the real ones should work).
3. Run a COPY of manual-run.sh? No: run the real file ${REPO}/manual-run.sh unchanged, with PATH set so that the fake ssh is found. The script writes its results to ${REPO}/tests/<date>-whole-chip-7200-manual-<time>/ : after EACH scenario delete exactly the folder that the scenario created there (its name is printed in the line "== run id ..."), and at the end confirm with "git -C ${REPO} status --short" that no such folder is left. Never delete any other folder of the repository.
Scenarios, each with the expected exit status and the key message: (a) happy path with -y: status 0, 12 result folders plus memcheck, go log and go2 log in the new tests folder, no folder of an older run, all three tables printed; (b) no argument and stdin "n": status 2 and the fake ssh was not called (make the fake ssh append to a call log); (c) wrong argument: status 2; (d) marker file present: status 3, no driver started; (e) local.sha mismatch: status 4; (f) go2.sha mismatch: status 4; (g) 10 modules (MemTotal 329000000 kB, and separately 10 lines from the fake sudo, and separately speed 8000 MT/s): status 5; (h) fake sudo fails (password needed): status 5; (i) stand-in go.sh exits 1 after writing 4 folders: status 10, the partial folders and the log are copied, go2 is not started; (j) go.sh fine but go2.sh exits 1: status 11; (k) go.sh exits 0 but one k120 folder has only 20 header lines: status 13; (l) go.sh exits 0 but one w120-T72C folder is missing: status 13; (m) fake ssh exits 255 at the driver call: status 255; (n) marker file appears after go.sh ended and before the copy: status 3 and a true message; (o) python3 fails (put a failing fake python3 first in PATH only for this scenario): status 14; (p) SIGINT sent to the script while the stand-in go.sh sleeps: status 130 and the message with the kill command (use setsid or a subshell to deliver the signal to the script; if you cannot make this scenario reliable in 3 tries, report it as not tested).
For every scenario record: the command, the exit status, the lines of output that matter, PASS or FAIL against the expectation. A FAIL is a finding. Also report anything else that looks wrong in the output (for example a misleading message, a table that is empty, leftover temp files in /tmp, a leftover go-direct.tmp).
Return findings (each with the scenario and the output as evidence) and in checked_ok one line per scenario that passed, plus the path of your harness runner script so it can be run again after a fix.`,
  { label: 'test:stand-in harness', phase: 'Test', schema: FINDINGS })

const reviewed = await pipeline(
  LENSES,
  l => agent(`${CONTEXT}\nYou are one of four independent reviewers. ${l.prompt}\nFor each finding give the line numbers, the proof (exact text, or a command you ran and its output) and a concrete failure scenario. Fewer, proven findings are better than many guesses. In checked_ok list what you verified as correct.`,
    { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }),
  (r, l) => {
    if (!r || !r.findings.length) return { lens: l.key, review: r, verdicts: [] }
    return agent(`${CONTEXT}\nYou are a skeptic. Another reviewer (lens: ${l.key}) reported the findings below about manual-run.sh. For EACH finding, try to refute it: read the lines, and where possible reproduce it with a small local experiment under ${SCRATCH}/verify-${l.key}/ (create it; no ssh, no remote machine). A finding is real only if you can show the wrong behavior or point at the exact lines that make it certain. A finding that re-opens one of the two user decisions, or that asks for a new feature, is not real. Default to real=false when you cannot prove it. For a real finding give the smallest fix as exact replacement text.\nFindings:\n${JSON.stringify(r.findings, null, 1)}`,
      { label: `verify:${l.key}`, phase: 'Verify', schema: VERDICTS })
      .then(v => ({ lens: l.key, review: r, verdicts: v ? v.verdicts : null }))
  }
)

const tester = await testerP
return { tester, reviewed }
