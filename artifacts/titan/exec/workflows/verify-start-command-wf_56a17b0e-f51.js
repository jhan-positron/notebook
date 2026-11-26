export const meta = {
  name: 'verify-start-command',
  description: 'Try to refute a draft of the manual start command for the CRB whole-chip run; one blind derivation for comparison',
  phases: [{ title: 'Verify' }],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771/scratchpad/startcmd'
const C = '/home/jhan/workspace/titan/cache-perf/crb'
const S = C + '/tmp/agent-scratch/w120-7200-2026-11-17'
const REC17 = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl'
const REC20 = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-pcie/b662db86-cbfe-4b4a-a59a-37f11dacb0e7.jsonl'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const RULES = `
HARD RULES (no exception):
- Do NOT use ssh, scp, rsync or any network login. Do NOT contact the machine 192.168.2.45 (CRB) in any way.
- Do NOT run go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, build12.sh or any benchmark binary. Reading them is fine.
- Do NOT edit any file outside your own scratch folder. Scratch folder: ${SP}/<your label> (create it). Do not edit ${SP}/draft.md.
- You may test shell text locally only with a fake HOME inside your scratch folder and with stub scripts (for example a go.sh that only prints text). Never start more than 2 busy processes.
- Do not send any project detail to an outside service. Public manual pages may be read.
- Report only what you verified. For each finding give the evidence (file and line, or the command you ran and its output).
`

const FILES = `
Files:
- Driver script: ${S}/go.sh (48 lines). Part A script: ${S}/ra.sh. Runner: ${C}/tmp/agent-scratch/w120-2026-11-15/rx.sh. Control script: ${S}/go2.sh.
- Checksum list copied to CRB on 2026-11-17: ${S}/local.sha
- Session record of the run of 2026-11-17 (JSON lines; the commands are tool_use entries with a "command" field): ${REC17} lines 309, 313, 339, 353, 365, 377. The tool results follow each command a few lines later.
- Session record of 2026-11-20 with the last known machine state of CRB: ${REC20} line 435 (tool result) and line 434 (command).
- Log of the run of 2026-11-17: ${C}/results/go-T72-20261117T221209Z.log
- Sharing rules for CRB: ${C}/jeremy-plan-constraints-2026-10-30.md
- Notes: ${MEM}/crb-ssh-login-first-command.md, ${MEM}/crb-check-dimm-count-every-use.md, ${MEM}/crb-whole-chip-rerun-7200-2026-11-17.md
- Recorded memory speed check of 2026-11-17: ${C}/results/dimm7200-20261117/try6.txt
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string', description: 'which claim or command of the draft (quote the part)' },
          verdict: { type: 'string', enum: ['wrong', 'incomplete', 'risky', 'confirmed'] },
          what: { type: 'string', description: 'what is wrong, missing or risky, in one or two sentences; or what was confirmed' },
          evidence: { type: 'string', description: 'file and line, or command run and its output' },
          fix: { type: 'string', description: 'exact corrected text or command, or empty' },
        },
        required: ['claim', 'verdict', 'what', 'evidence'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const LENSES = [
  {
    key: 'shell',
    prompt: `Lens: shell and ssh semantics. Read ${SP}/draft.md. For every command block of the draft, decide whether it does exactly what the draft says when a user types it in bash on the agent server.
Check at least: quoting of the single-quoted remote command (double quotes, $(...), $B, $L, $pid, ~ expansion on the remote side, the multi-line form); whether the sed line changes exactly one line of go.sh and nothing else (test on a copy of the real go.sh in a fake HOME); the "a && b || exit 4" form; whether pid=$! is the pid of the go script when nohup and setsid are used in a non-interactive ssh shell (compare with what the record of 2026-11-17 printed: "log ... pid ..." against the first line of the log "go.sh pid ..."); whether "wait $pid" and the printed exit status are right; whether the run survives a dropped ssh connection or a Ctrl-C of the user and why; whether "kill -TERM -- -P" stops everything; what ssh -t does for the sudo command; whether "ls -l /tmp/positron-perf.RUNNING" of the check command ends the remote command early (it must not); whether the options -o BatchMode=yes that the record used and that the draft left out matter for a manual run.
Run local dry tests with stub scripts in a fake HOME (bash -c "<remote text>"), never ssh.`,
  },
  {
    key: 'preconditions',
    prompt: `Lens: preconditions and behavior of the scripts. Read ${SP}/draft.md, then go.sh, ra.sh, rx.sh and go2.sh line by line.
List every check in these scripts that can stop a new run today, in the order they execute, and say for each whether the draft names it and whether the draft's claim about it is right. Verify claim 2 fully: with the boot id of 2026-11-20 (see the record), does the unchanged go.sh end at line 26, with which text and exit status, and does any benchmark process or result folder get created before that point (look at lines 19 to 27: the lock file, the echo lines)? Verify from the record of 2026-11-20 that the reboot time, boot id and MemTotal in the draft are exact.
Verify claim 4: after the one-line change, which checks remain that could still fail (for example MemTotal threshold, sha256 of rx.sh and bwx12, the files that ra.sh needs under scratch-kernels-20261113, the "at most 2 runnable tasks" wait of ra.sh, the marker file). Is the list of files in the draft's check command complete for everything go.sh, ra.sh and rx.sh need on CRB? Is the run length "about 10 minutes" right (use the log and the launch times)? Are the folder names right? Does anything in the scripts make a second run with the same step names T72A1..T72C4 fail or mix with the folders of 2026-11-17 (look at rxok in go.sh: ls ... | tail -1, and at how ra.sh and rx.sh name folders)? Is the statement about go2.sh right?
Also say what the user sees on the screen when everything works (first and last lines).`,
  },
  {
    key: 'rules',
    prompt: `Lens: rules for the shared machine and for the data. Read ${SP}/draft.md, then the sharing rules file and the three notes.
Decide for each step of the draft whether it obeys the rules: no login during a block, the marker file, CPUs 0 to 119 only, no root for the run, the standing instruction to check the memory module count and speed at each use, how early a block is announced (the draft says the newest notice in the Slack channel is a block that ended Sat 21 Nov 07:32 UTC; you cannot read Slack, so judge only whether the draft's advice about the channel is sufficient given the announcement lead times in the notes and the rules file, and given that the two newest blocks started at 04:00 UTC).
Check whether the draft leaves out a warning that the rules or notes require (for example: a 120-thread run of about 10 minutes must be finished or stopped before a block starts; who else uses the machine; what to do if MemTotal shows 10 modules; that sudo is the user's decision). Check whether changing the boot id by a copy of the script weakens the purpose of the check in go.sh line 26, and whether the draft's procedure (read boot id and memory speed first, then put that literal boot id into the copy) keeps that purpose. Check the claim about data: would a new run with the same step names disturb the local analysis scripts (${S}/facts_data.py holds typed folder names; ${S}/stat_bwx.py and stat_k120.py take folder arguments) when the user later copies the new folders into ${C}/results? Give the exact lines.`,
  },
]

phase('Verify')
const results = await parallel([
  ...LENSES.map(l => () => agent(
    `You are checking a draft answer before it is given to an engineer. Try to REFUTE it. Report every statement or command that is wrong, incomplete or risky. Also report the important statements that you confirmed.\n${RULES}\n${FILES}\n${l.prompt}`,
    { label: `refute:${l.key}`, phase: 'Verify', schema: FINDINGS })),
  () => agent(
    `An engineer asks: "Write me the command which I run manually here to start a run." "Here" is a bash shell on the agent server. The run is the whole-chip read test of 2026-11-17 on the machine CRB (192.168.2.45, user jhan, ssh key /home/jhan/.ssh/id_ed25519). Derive the answer yourself from the records and scripts below. Do NOT read any file under ${SP} except files that you create in your own scratch folder ${SP}/blind.\n${RULES}\n${FILES}\nWork: (1) find the command that started go.sh on 2026-11-17 in the session record; (2) read go.sh, ra.sh and rx.sh and decide whether the same command would start a run today, given the last known machine state of CRB in the record of 2026-11-20; (3) if not, give the smallest change that lets the user start a run, without weakening what the failing check protects; (4) list what the user must check before the start and what the user sees when it works. Return the exact command text and the reasons, each with its evidence.`,
    { label: 'blind-derivation', phase: 'Verify', schema: {
      type: 'object',
      properties: {
        recorded_command: { type: 'string' },
        works_today: { type: 'string', description: 'yes or no, with the reason and evidence' },
        proposed_commands: { type: 'string', description: 'exact command text the user should type, in order' },
        checks_before_start: { type: 'array', items: { type: 'string' } },
        notes: { type: 'array', items: { type: 'string' } },
      },
      required: ['recorded_command', 'works_today', 'proposed_commands', 'checks_before_start', 'notes'],
    } }),
])
log('agents done: ' + results.filter(Boolean).length + ' of 4')
return { shell: results[0], preconditions: results[1], rules: results[2], blind: results[3] }
