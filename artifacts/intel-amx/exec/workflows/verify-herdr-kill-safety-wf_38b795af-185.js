export const meta = {
  name: 'verify-herdr-kill-safety',
  description: 'Independently try to refute: killing herdr servers 3077789 and 3246526 inside claude-agentsrv loses only idle shells',
  phases: [{ title: 'Refute' }],
}
const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    evidence: { type: 'string' },
    extra_risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['refuted', 'evidence', 'extra_risks'],
}
const CLAIM = `CLAIM under test: Inside the claude-agentsrv container (you are root, HOME=/home/jhan), the two processes
"/home/jhan/.local/bin/herdr server" with pids 3077789 (started 20:44 PDT) and 3246526 (started 20:55 PDT) can be stopped
without losing any running work. Each pane under them is an idle /bin/sh with no children (pids 3077823 3077826 3077829 3077832 3077835 under 3077789; 3250371 under 3246526), and "herdr agent list" on both servers returns an empty list.
3077789 serves the default session (sockets in /home/jhan/.config/herdr/), 3246526 serves "--session claude-agentsrv" (sockets in /home/jhan/.config/herdr/sessions/claude-agentsrv/).
READ-ONLY RULES: do NOT kill, signal, stop, or restart anything. Do NOT run any "herdr server stop", "kill", "pkill" or write into ~/.config/herdr. Use only ps, /proc, ss, ls, cat, grep, pstree, and read-only herdr subcommands (status, pane list, pane read, api snapshot, agent list).
Return refuted=true only if you find concrete evidence (a live agent, a child process, unsaved state, a connected client doing work, or a mechanism by which stopping these harms something else). Default to refuted=false if you find nothing. List any extra risks (e.g. stale socket files, respawn by login hooks, session.json overwrite) as extra_risks with the evidence.`
const LENSES = [
  'LENS: process tree. Walk every descendant of both servers via /proc and pstree. Check every pty (pts/79-83, pts/87) for ANY process attached, including processes reparented to pid 1. Check /proc/<sh>/status for threads and for pending signals, and check pane shells\' fd 0/1/2 and any background jobs.',
  'LENS: herdr runtime state. Use read-only herdr commands: "herdr pane list", "herdr pane read <pane_id>" for each pane (shows scrollback - look for a running agent prompt or in-progress command), "herdr agent list", "herdr api snapshot", and the same with "--session claude-agentsrv". Also tail /home/jhan/.config/herdr/herdr-server.log and herdr-client.log for connected clients still attached right now.',
  'LENS: side effects of stopping. Investigate what happens AFTER stopping: does /home/jhan/agentsrv-setup.sh respawn a session server at next login? Will stale socket files block a new server (look at the client log around 2026-10-04T03:44Z for how a new server came up over existing socket files)? Does session.json (3 workspaces, saved 20:45) survive? Is there any evidence of a host-side herdr server (pid 4168986 from the host) that these two could affect? Compare "herdr server stop" vs kill -TERM vs kill -9 using "herdr server --help" and "herdr status".',
]
phase('Refute')
const votes = await parallel(LENSES.map((l, i) => () =>
  agent(`${CLAIM}\n\n${l}\n\nReport exact commands run and outputs that matter.`, { label: `refute:${i}`, phase: 'Refute', schema: VERDICT })))
const v = votes.filter(Boolean)
log(`${v.length}/3 verifiers returned; refuted by ${v.filter(x => x.refuted).length}`)
return { votes: v }