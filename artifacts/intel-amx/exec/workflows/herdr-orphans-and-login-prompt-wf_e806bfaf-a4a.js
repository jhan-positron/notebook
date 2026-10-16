export const meta = {
  name: 'herdr-orphans-and-login-prompt',
  description: 'Adversarially verify the orphan kill list (read-only) and design/test login-prompt placements',
  phases: [
    { title: 'Refute kill list', detail: '3 independent read-only skeptics' },
    { title: 'Design prompt placement', detail: '3 independent approaches, each pty-tested' },
    { title: 'Judge designs', detail: 'rank the tested approaches' },
  ],
}

const KILL = [
  // [herdr client pid, bash -l parent pid, conmon pid]
  [2536329,2534396,2534389],[1011306,1009732,1009712],[3958039,3954219,3954216],[1367581,1365074,1365071],
  [3903260,3901752,3901748],[1561152,1559126,1559119],[3140745,3140479,3140476],[1444854,1444613,1444608],
  [2196380,2194711,2194708],[1400046,1398507,1398504],[380394,377755,377750],[1918478,1911263,1911255],
  [2755940,2754310,2754133],[867530,867283,867279],[2307525,2306143,2306139],[475357,471267,471250],
  [4152422,4143118,4143115],[433819,428948,428940],[1890284,1888620,1888617],
]
const KEEP = [[1906010,1904196,1904193,1904123],[1968531,1965271,1965267,1965198]]

const VERDICT = { type:'object', required:['refuted','confidence','reasons','unsafe_pids'], properties:{
  refuted:{type:'boolean'}, confidence:{type:'string', enum:['low','medium','high']},
  reasons:{type:'array', items:{type:'string'}}, unsafe_pids:{type:'array', items:{type:'integer'}},
  checks_run:{type:'array', items:{type:'string'}} } }

const refutePrompt = (lens) => `You are a skeptical verifier on host agentsrv (Linux, user jhan, shared NFS home). READ-ONLY: you must not send any signal, kill, pkill, podman stop/kill, or edit any file. You may run ps, ls -l /proc/<pid>/fd, cat /proc/<pid>/{status,stat,cmdline,cgroup}, readlink, journalctl --user, last, grep on logs under ~/.config/herdr/.

CLAIM to refute: each triple [herdr_client_pid, bash_parent_pid, conmon_pid] in this list is an ORPHAN that can be killed without losing anything: ${JSON.stringify(KILL)}.
The claim's basis: each herdr process is an interactive herdr CLIENT (TUI) running inside the podman container 'claude-dev' (its stdin/stdout is a container pty), started by 'podman exec -it ... bash -l' from an ssh session that has since closed. The host-side 'podman exec' process for each closed session is gone; only three 'podman exec -it' processes remain alive on the host (pids 1904123 started 20:45:19, 1965198 at 20:48:17, 2422443 at 21:08:49 on 2026-10-03), and those back the KEEP set ${JSON.stringify(KEEP)} (format [herdr, bash, conmon, podman-exec]) and a claude shell, not the kill list. herdr clients hold no state: the state lives in 'herdr server' processes (pids 1890285 default session, 2123340 named session) which must NOT be touched. A herdr server survives its spawning client exiting (observed: client 2123339 is gone, server 2123340 still runs).

Your lens: ${lens}. Try hard to find any pid in the list that is (a) still backed by a live ssh/podman-exec session a human could be looking at, (b) actually a server or holds unsaved state, (c) would take down a herdr server, a pane, an agent (claude/codex), or a tmux session if killed, or (d) is not what the claim says it is. Check child processes of each pid (pgrep -P). Note conmon processes are host-side helpers for each exec session; killing the exec'd bash makes conmon exit by itself. Default to refuted=true only if you find concrete evidence; list the exact pids that are unsafe in unsafe_pids. Report the checks you ran.`

const DESIGN_CONSTRAINTS = `Context (host agentsrv, user jhan, bash, shared NFS home across hosts alpha/sw-dev-01/agentsrv):
- ~/.profile sources ~/.bashrc and THEN prepends ~/bin and ~/.local/bin to PATH.
- ~/.bashrc line 7 sources ~/jibin.bashrc.positron.dev (common file) BEFORE it appends ~/bin (line 13). That common file sources the per-host file "$HOME/$(hostname)-setup.sh" (line 23) and only afterwards prepends ~/.local/bin (line 27). .bashrc sources the common file twice (lines 7 and 9).
- The per-host file ~/agentsrv-setup.sh currently ends with this block (added by Codex on 2026-10-02):
if [[ $- == *i* && -t 0 && \${_HERDR_LOGIN_PID:-} != "$$" ]] && shopt -q login_shell; then
    _HERDR_LOGIN_PID=$$
    read -r -p 'run claude-dev to start container and start herdr? Y/* ' _herdr_reply
    [[ $_herdr_reply == [yY] ]] && "$HOME/claude-container/claude-box" start && podman exec -it -e IS_SANDBOX=1 -w /home/jhan claude-dev bash -lic 'herdr --session "$(hostname)"; exec bash -l'
    unset _herdr_reply
fi
- Verified defect: pressing Ctrl-C at that read aborts the REST of all startup files (bash abandons startup on SIGINT), so PATH lacks ~/bin and ~/.local/bin and 'claude-box', 'herdr', 'codex', 'claude' are "command not found" in that shell. Answering n is fine.
- The user's constraint: the per-host file must stay host-specific and stay sourced by the common file. They asked for alternatives OTHER than "move the prompt to the end of ~/.bashrc" and asked about "wrap the read so Ctrl-C cannot abort". Touching common files is allowed only if the change is tiny and generic (e.g. a second late hook), but a solution that changes ONLY the per-host file is preferred.
- Inside the container the hostname is claude-agentsrv so the per-host file is not sourced there; keep it that way.

RULES: Do NOT edit any real file under /home/jhan. Build your prototype in a fake HOME under /tmp/claude-644434775/-home-jhan-workspace-random/c7b1e2c1-2bb3-489b-af22-c6a5ac1846a3/scratchpad/design-<yourname>/ with a .profile, .bashrc, common.sh and <host>-setup.sh that mirror the real ordering above (use a stub instead of the real podman command: e.g. echo WOULD-START). Test with a python pty harness running 'bash -l' with HOME set to the fake home (write the harness yourself; os.environ HOME then execvp bash -l inside pty.fork). Required test matrix, each reporting PATH contains both the .bashrc-added and .profile-added entries, and whether WOULD-START ran:
 T1 Ctrl-C (\\x03) at the prompt; T2 'n' + Enter; T3 'y' + Enter; T4 non-interactive 'bash -lc true' must not prompt and must not hang (use timeout 5); T5 interactive NON-login shell 'bash -i' must not prompt; T6 prompt appears exactly once per login shell even though the common file is sourced twice; T7 a second login shell (new bash -l) prompts again (so the guard is per shell, not per machine).
Return: the exact proposed content of the per-host block (and any tiny common-file change if your approach needs one), the harness results per test as PASS/FAIL with the observed output line, caveats (e.g. behaviour when the user presses Ctrl-C during the podman exec itself, double prompting, interaction with 'exec bash -l'), and a one-paragraph plain-English explanation of why it works.`

const DESIGN = { type:'object', required:['approach','block','common_file_change','tests','caveats','explanation'], properties:{
  approach:{type:'string'}, block:{type:'string'}, common_file_change:{type:'string'},
  tests:{type:'array', items:{type:'object', required:['id','result','observed'], properties:{id:{type:'string'}, result:{type:'string', enum:['PASS','FAIL','NOT_RUN']}, observed:{type:'string'}}}},
  caveats:{type:'array', items:{type:'string'}}, explanation:{type:'string'} } }

const APPROACHES = [
  { name:'trap', brief:'Keep the read exactly where it is in the per-host file, but make Ctrl-C harmless: install a temporary INT trap (or ignore INT) around the read so bash does not abandon startup, treat an interrupted read as "no", and restore the trap afterwards. Also consider "read -t <seconds>" with a default of no. Verify with the harness whether a trapped SIGINT still aborts the sourced file or not; report what you actually observe.' },
  { name:'prompt-command', brief:'Keep the per-host file as the only edited file, but DEFER the prompt: the per-host file only defines a function and arms a one-shot PROMPT_COMMAND (or a DEBUG-trap one-shot) so the question runs right before the first interactive prompt, after ALL startup files have finished and PATH is complete. The function must remove itself from PROMPT_COMMAND (preserve any pre-existing PROMPT_COMMAND), and must only arm itself for interactive login shells.' },
  { name:'late-hook', brief:'Add a second, generic, late per-host hook: one line appended at the very END of ~/.profile (after its PATH lines) or at the very end of ~/.bashrc, of the form [ -r "$HOME/$(hostname)-login.sh" ] && . "$HOME/$(hostname)-login.sh", and move the prompt block into ~/agentsrv-login.sh (so host-specific content stays in a host file). Also fix the early block so a Ctrl-C there cannot hurt (no read left in the early file). Discuss .profile vs .bashrc placement: .profile runs only for login shells, which removes the need for the login_shell test, but check what happens for login shells that are non-interactive.' },
]

phase('Refute kill list')
const lenses = [
  'liveness: prove or disprove that no live terminal/ssh/podman-exec session is attached to each pid; use /proc fds, ps -o tty,sid,pgid, host "podman exec" processes, journalctl --user and last -F for session end times',
  'collateral damage: enumerate every descendant of every pid in the list and confirm none is a herdr server, claude, codex, tmux server, or anything with unsaved state; confirm the two herdr servers are not descendants',
  'identity: confirm each listed herdr pid really is an interactive client of herdr (not server, not api command) and each bash pid is its parent login shell inside container claude-dev; check cmdline, cgroup, environ HOSTNAME, and that the parent-of-bash is a conmon',
]
const refutersP = parallel(lenses.map((l,i) => () => agent(refutePrompt(l), { label:`refute:${i+1}`, phase:'Refute kill list', schema: VERDICT })))

phase('Design prompt placement')
const designsP = parallel(APPROACHES.map(a => () => agent(`${DESIGN_CONSTRAINTS}\n\nYOUR APPROACH (name: ${a.name}): ${a.brief}\nUse scratch dir name design-${a.name}.`, { label:`design:${a.name}`, phase:'Design prompt placement', schema: DESIGN })))

const [refuters, designs] = await Promise.all([refutersP, designsP])
const validDesigns = designs.filter(Boolean)
log(`refuters done: ${refuters.filter(Boolean).length}/3; designs done: ${validDesigns.length}/3`)

phase('Judge designs')
const JUDGE = { type:'object', required:['ranking','recommended','why','risks'], properties:{
  ranking:{type:'array', items:{type:'string'}}, recommended:{type:'string'}, why:{type:'string'},
  risks:{type:'array', items:{type:'string'}}, re_tested:{type:'array', items:{type:'string'}} } }
const judge = validDesigns.length ? await agent(`You are judging three tested proposals for where a login-time "start container + herdr?" prompt should live, under this context:\n${DESIGN_CONSTRAINTS}\n\nProposals (JSON):\n${JSON.stringify(validDesigns, null, 1)}\n\nRe-run the critical test yourself for the top two candidates (Ctrl-C at the prompt must leave PATH complete; non-interactive bash -lc must not prompt or hang) using their fake homes under the scratchpad (do not edit real files, do not kill anything). Rank them by: correctness under Ctrl-C, no change to common files (or smallest possible), no double prompt, simplicity, and robustness to the 'bash -lic' container entry. Give a plain-English recommendation.`, { label:'judge', phase:'Judge designs', schema: JUDGE }) : null

return { refuters: refuters.filter(Boolean), designs: validDesigns, judge }