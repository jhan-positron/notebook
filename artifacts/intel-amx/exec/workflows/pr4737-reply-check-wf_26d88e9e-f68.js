export const meta = {
  name: 'pr4737-reply-check',
  description: 'Check the six draft replies to the PR 4737 review: plain English and facts against the commits',
  phases: [{ title: 'Check', detail: '2 lenses per reply' }],
}
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-i4500'
const SP = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/922a3361-aa01-4c82-918d-776e08c4d97d/scratchpad'
const REPLIES = ['C1', 'C2', 'C3', 'C4', 'C5', 'G']
const CTX = `Context: tron PR #4737 (branch jhan-amx-vnniK-i4500) got five inline review comments (ids in ${SP}/comments.json, bodies there) and a C++-guide note in the review body. The responses are three commits on top of 452b2052c9 in the worktree ${WT} (read-only): d8f6c479bc (C2: k_storage_ref parameter), a9923ddd97 (C3, C4, C5: comment passages), 9e813a8ce5 (G: named literals). Draft replies are in ${SP}/replies/<key>.md; the mapping is C1..C5 = the five inline comments in the order of comments.json, G = the review-body C++ guide note. Use git (read-only: git show, git diff, git log) in the worktree to see each commit. Return raw data for the orchestrator.`
const SCHEMA = {
  type: 'object',
  properties: {
    reply: { type: 'string' },
    lens: { type: 'string' },
    problems: { type: 'array', items: { type: 'object', properties: { phrase: { type: 'string' }, issue: { type: 'string' }, fix: { type: 'string' } }, required: ['phrase', 'issue', 'fix'] } },
    corrected: { type: 'string', description: 'the full corrected reply text (identical to the draft when nothing is wrong)' },
  },
  required: ['reply', 'lens', 'problems', 'corrected'],
}
const LENSES = [
  { name: 'facts', prompt: 'Lens: FACTS. Every claim in the draft must be true of the commit it names (file names, function names, which commit did what, line numbers, counts, what was left unchanged). Verify each against the worktree and the commits with git show. For C1, verify the CI facts in the repository files named (gcp-nix.yml, nix/cmake-tron-test-build.nix, cmake-single-platform.yml, publish-deb.yml, CMakeLists.txt, src/tron/CMakeLists.txt, AGENTS.md) and `git log` for the commits named (f4889f8072, 929fa94e42, 2f1ee29982); for C5, the measurement claims come from the author\'s campaign notes and cannot be verified in the repo: leave them, but flag any wording that overstates them. Also check: no person is named (roles only) and no commit id is wrong.' },
  { name: 'english', prompt: 'Lens: PLAIN ENGLISH, per these rules: define a term at first use when it is a code name, acronym or metric (a GitHub reply is one document; the reviewer knows the code, so a function name in backticks needs no definition, but acronyms and build names do); one claim per sentence (split on "because", "since", "which means", "so that", semicolons); numbers carry units and a meaning; no idioms or metaphors; short sentences; bullets for several separate points. Keep the reply short (the C2-C5 ones under 150 words; C1 and G may be longer). Do not change the technical content.' },
]
const results = await pipeline(REPLIES, key => parallel(LENSES.map(l => () =>
  agent(`${CTX}\n\nCheck the draft reply ${key} (file ${SP}/replies/${key}.md).\n\n${l.prompt}`,
    { label: `check:${key}:${l.name}`, phase: 'Check', schema: SCHEMA })
)).then(vs => ({ key, checks: vs.filter(Boolean) })))
return results