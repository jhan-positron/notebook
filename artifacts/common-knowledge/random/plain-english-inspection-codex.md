**Short version**

The skill needs clearer guidance on when splitting helps. Keep short, simple clauses together. Use bullets when several developed points or steps become difficult to follow in prose.

**Revised scope**

Your cache example sets an important boundary: different perspectives alone do not require bullets. Each clause is short and easy to understand.

The earlier report went too far:

- It treated separate claims and ordered steps as automatic reasons to create lists.
- It proposed word limits without evidence that they matched your preference.
- It added labels such as “Benefit” and “Cost,” which interrupted smooth reading.

This inspection now focuses on sentence complexity and useful grouping. The recommendations below replace those earlier proposals.

**What needs clarification in the skill**

- Rule 2 says “One claim per sentence.” Read literally, this can split a simple sentence unnecessarily. Allow closely related claims when their clauses are short and clear. [Ref1]
- Rule 3 focuses on the number of dependent clauses. These are clauses such as “because the queue was full.” Their length and nesting also matter. A brief condition can remain in the sentence. [Ref2]
- Rule 4 requires bullets for “several separate points.” It does not distinguish a compact sentence from a paragraph of developed perspectives. The final check also accepts blank lines in place of bullets. Clarify when a list makes the relationship easier to follow. [Ref3] [Ref4]

The skill should address sequences explicitly. A short sequence can stay in prose. Steps with their own conditions or explanations are better candidates for a list. [Ref3]

**Suggested wording**

Replace the relevant rules with this smaller set of instructions.

**Rule 2 — Keep each sentence easy to follow**

Prefer one main point per sentence. Closely related claims can share a sentence when each clause is short and simple.

**Rule 3 — Prefer short sentences without making the prose choppy**

Split sentences with long or nested clauses. Keep brief conditions and simple connections together when they read naturally. Preserve the original meaning when splitting.

**Rule 4 — Use lists when they make the structure clearer**

Use bullets when a paragraph develops several perspectives on the same subject. Use a list when a sequence contains steps that need separate attention. Use numbering when the order matters.

Keep compact sentences and short sequences in prose when they are easy to follow. Do not add category labels to bullets unless the labels help the reader.

**Examples that show the boundary**

Keep the cache example as one sentence:

> The cache reduces repeated reads, uses more memory, and needs explicit invalidation.

Its clauses are brief. Separate bullets would add little, and category labels would interrupt the sentence’s natural flow.

Use bullets when the same subject needs fuller explanations.

Before:

> The cache avoids repeated reads when requests reuse the same records. It retains those records in memory until eviction, so memory use grows with the retained data. Writers must invalidate changed records before later requests read them, or those requests may receive stale values.

After:

- The cache avoids repeated reads when requests reuse the same records.
- It retains records in memory until eviction. Memory use grows with the retained data.
- Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

The bullets separate developed points. Each starts directly with its content.

Keep a brief sequence in prose:

> Check the lease, start the run, then save the log.

Use a numbered list when each step needs its own detail:

1. Check the lease. Stop if another campaign holds it.
2. Start the run. Wait for it to finish before collecting results.
3. Save the log with the run identifier. Keep failed-run logs too.

Split a complex sentence without automatically creating bullets.

Before:

> Because the reader, which starts before initialization finishes, can observe an empty queue, the test sometimes fails.

After:

> The reader starts before initialization finishes, so it can observe an empty queue. That can cause the test to fail.

This is one short causal explanation. A paragraph preserves its flow.

**Final check to add**

- Are any clauses long or nested enough to require rereading? Split them.
- Does a paragraph contain developed perspectives or steps that would be easier to follow as a list? Separate them.
- Did splitting create tiny bullets or choppy sentences? Combine them where that restores natural flow.
- Did added labels repeat what the text already says? Remove them.

**Inspection limits**

These findings come from the skill text and your feedback. The examples illustrate the proposed behavior; they are not test results. The installed skill has not been changed.

**Insufficient data:** the revised wording has not been tested against generated outputs. Comparing outputs on these examples would show whether it preserves simple sentences while improving dense passages.

**References**

- [Ref1] [Rule 2: one claim per sentence](/home/jhan/.codex/skills/plain-english/SKILL.md:28), lines 28–35.
- [Ref2] [Rule 3: short sentences](/home/jhan/.codex/skills/plain-english/SKILL.md:37), lines 37–39.
- [Ref3] [Rule 4: bullets and blank lines](/home/jhan/.codex/skills/plain-english/SKILL.md:41), lines 41–43.
- [Ref4] [Final self-check](/home/jhan/.codex/skills/plain-english/SKILL.md:109), lines 109–120.
