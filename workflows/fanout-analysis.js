export const meta = {
  name: 'fanout-analysis',
  description: 'Parallel read-heavy analysis with cheap Sonnet agents: N readers -> synthesis -> adversarial citation check. The measured sweet spot between a solo session and full dirigent ceremony (~$2.50 for 8 files / 3.5k lines in the 07/2026 benchmark).',
  whenToUse: 'Parallelizable volume across independent files where coverage and fresh-context verification matter. Not for single reasoning chains (unknown bugs, architecture decisions) — those stay solo.',
  phases: [
    { title: 'Read', detail: 'one Sonnet reader per file pair', model: 'sonnet' },
    { title: 'Synthesize', detail: 'merge raw material into one report', model: 'sonnet' },
    { title: 'Verify', detail: 'adversarial spot check of 6 citations', model: 'sonnet' },
  ],
}

// args: { root: "/abs/path/to/repo", files: ["rel/a.py", "rel/b.py", ...], task?: "focus hint" }
// All agents run on Sonnet at high effort — this is dirigent's model-arbitrage
// idea in workflow form, and the whole point of this script. Remove the
// overrides and every agent inherits the (expensive) session model instead.
const A = typeof args === 'string' ? JSON.parse(args) : args
const ROOT = A.root
const FILES = A.files
const TASK = A.task || 'general code quality and robustness'
const OPTS = { model: 'sonnet', effort: 'high' }

if (!ROOT || !FILES || !FILES.length) {
  throw new Error('args required: { root: "/abs/path", files: ["rel/path", ...], task?: "focus" }')
}

// Deterministic pairing (no randomness allowed in workflow scripts).
const pairs = []
for (let i = 0; i < FILES.length; i += 2) pairs.push(FILES.slice(i, i + 2))

phase('Read')
const readerPrompt = (files) => `Read the following file(s) COMPLETELY with the Read tool: ${files.map(f => ROOT + '/' + f).join(' and ')}.

Analysis focus: ${TASK}.

Produce (compact Markdown, at most ${35 * files.length} lines TOTAL):
1. Inventory per file (max 10 lines each): responsibility, most important public classes/functions with exact line numbers, dependencies.
2. EXACTLY ${2 * files.length} findings (2 per file): code-quality or robustness problems, each with an exact file:line citation and a fix suggestion in max 3 lines. Line numbers WILL be verified later — they must be exact.
3. Cross-cutting raw notes (max 6 lines): recurring patterns, shared risks, with file:line.

Your return text is raw material for a synthesizer, not a user-facing message. No introduction, no conclusion.`

const reads = await parallel(pairs.map((pair) => () =>
  agent(readerPrompt(pair), { ...OPTS, label: 'read:' + pair.join('+'), phase: 'Read' })))
const material = reads.filter(Boolean)
log(material.length + '/' + pairs.length + ' reader results collected')

phase('Synthesize')
const report = await agent(`You receive raw analysis material about ${FILES.length} files (checkout at ${ROOT}). Produce the full content of a REPORT.md (max 250 lines) with exactly this structure, returned as plain text (do NOT write any file):

1. Inventory (max 80 lines): per file its responsibility, most important public classes/functions with line numbers, dependencies.
2. Findings (EXACTLY ${2 * FILES.length}, two per file): sorted by relevance, each with a file:line citation and a concrete fix suggestion (max 4 lines each). Pick the strongest 2 per file from the material.
3. Cross-cutting check (max 40 lines): recurring patterns and shared risks across files, with file:line from the material.

Copy file:line citations UNCHANGED from the material — invent nothing. Your answer starts directly with "# " (the report itself, nothing else).

=== RAW MATERIAL ===

${material.join('\n\n=== NEXT READER ===\n\n')}`, { ...OPTS, label: 'synthesize', phase: 'Synthesize' })
log('report: ' + String(report).length + ' chars')

phase('Verify')
const verify = await agent(`Below is an analysis report about files under ${ROOT}/. Pick 6 findings spread across different files, open each cited file at the cited line (Read tool with offset), and check whether the claim actually holds there. Return exactly 6 lines in the format "<file:line> OK|WRONG — <one sentence>" plus a final line "Verdict: n/6 correct". No other output.

=== REPORT ===

${String(report)}`, { ...OPTS, label: 'verify:citations', phase: 'Verify' })

return { readers: material.length, report: String(report), verify: String(verify) }
