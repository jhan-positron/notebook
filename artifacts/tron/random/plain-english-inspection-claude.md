# Inspection of the plain-english skill

Written 2026-11-20 by Claude (model Fable 5.2). Revised the same day after a review of the Codex inspection.

The plain-english skill is the rule file that tells Claude how to write for you. I did not change it.

## Short version

Measurement confirms that Claude's recent outputs still hold long sentences and long paragraphs. The skill's two rules against them changed nothing measurable in a controlled test. A reworded skill cut sentences over 20 words from 6.3% to 0% and kept short sentences whole.

## What changed in this revision

- You gave Codex a boundary: a sentence with short, simple clauses stays whole [Ref17]. I adopted it.
- You told Codex that labels such as "Benefit" are "against smooth reading" [Ref17]. I removed such labels from the proposal and from this report.
- My first proposal broke both points. It turned your cache sentence into a list in 3 of 3 runs.
- The revised proposal keeps that sentence whole in 3 of 3 runs. It still gives 0% long sentences.
- I tested the wording that Codex suggests. It keeps the sentence whole too. It gives 11.8% long sentences, against 6.3% for the current skill.
- I corrected an error of mine. My script had skipped rewritten text inside code fences. Section 10 holds the corrected numbers, and no conclusion changed.

## Words used here

- **Skill**: the file `~/.claude/skills/plain-english/SKILL.md`.
- **CLAUDE.md**: the instruction file that Claude Code loads in every session. Yours imports the skill. So the skill text is in every session.
- **Context**: the text that the model sees in one session.
- **Transcript**: the saved record of one session.
- **Subagent**: a helper session that a main session starts.
- **Codex**: the other coding assistant that you asked for the same inspection [Ref16].
- **Rule 3, Rule 4**: the skill's rules "Use short sentences" and "Use bullet points and blank lines to separate points".
- **Long sentence**: in this report, a sentence of more than 20 words.
- **Join**: ", and", ", or", ", but" or ", so" between two parts of one sentence.
- **Subordinating word**: a word that opens a dependent clause. The script counts these: because, since, although, unless, while, when, if, until, so that, which, whose, where.
- **Cache sentence**: your example of a sentence that must stay whole. "The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation."
- **Short version**: the opening summary that Rule 7 of the skill requires.
- **Fable 5.1, Fable 5.2**: two versions of the Claude model.
- **Checker**: the script `check_lengths.py`, written for this inspection [Ref10]. It counts words per sentence and sentences per paragraph.
- **Run**: one Claude session without a user present. It answers one writing task once.

## 1. What I inspected

- The skill file has 120 lines and 1,038 words. It was last changed on 2026-11-15 [Ref1].
- I recovered its earlier versions from session transcripts [Ref2] [Ref3].
- I checked that the skill text reaches main sessions and subagents [Ref5].
- I measured 766 chat replies written after 2026-11-10, and 12 report files changed after 2026-11-15 [Ref6].
- I searched your prompt history for requests about sentence length and bullets [Ref7].
- I ran a controlled test: 75 runs with six versions of the skill text on one model [Ref9].
- I read the Codex inspection and your reply to its first version [Ref16] [Ref17].

## 2. History of the two rules

Three facts matter for reading the data.

- The two rules are not new. They have been in the skill since at least 2026-09-11, as Rules 7 and 8 [Ref2].
- On 2026-11-10 they moved up and became Rules 4 and 3. The title "Prefer short sentences" became "Use short sentences". The body text did not change [Ref3].
- On the same day your sessions went from Fable 5.1 to Fable 5.2 [Ref4].

So real outputs before and after 2026-11-10 differ in two things at once. Section 10 separates them.

## 3. Both observations are confirmed

```
Sentences over 20 words. One block = 2 percentage points.

Real outputs
chat, before 2026-11-10    █████████████ 25.5%
chat, after 2026-11-10     ██████ 12.8%
12 reports, after          ███████ 13.4%
"Short version" blocks     ████████████████████████ 48.1%

Controlled test, model Fable 5.2 (section 10)
A  no Rules 3 and 4        ████ 7.4%
B  rule order until 11-10  ████ 8.1%
C  current skill           ███ 6.3%
X  Codex wording           ██████ 11.8%
D1 my first proposal        0.0%
D2 revised proposal         0.0%
```

One sentence in eight is still long. In the test, only the two proposals with a word limit removed them.

| Measure | Chat before 2026-11-10 | Chat after | 12 reports after |
|---|---|---|---|
| Model | Fable 5.1 | Fable 5.2 | Fable 5.2 |
| Replies or files | 1,271 | 766 | 12 |
| Sentences | 9,176 | 6,324 | 4,126 |
| Mean words per sentence | 15.4 | 12.4 | 12.3 |
| Sentences over 20 words | 25.5% | 12.8% | 13.4% |
| Sentences over 25 words | 14.2% | 4.8% | 6.7% |
| Paragraphs over 3 sentences | 11.2% of 2,718 | 2.0% of 1,388 | 15.6% of 793 |
| Bullets over 3 sentences | 11.0% of 1,630 | 3.0% of 2,429 | 11.7% of 1,182 |
| Share of prose words in bullets | 41.0% | 61.4% | 60.3% |

What the table says:

- Long sentences remain. After 2026-11-10, 1,358 of 10,450 sentences exceed 20 words. That is 13.0% [Ref6].
- Long paragraphs remain in reports. 15.6% of report paragraphs have more than three sentences. In chat replies the share is 2.0%.
- Some bullets are paragraphs. 11.7% of report bullets have more than three sentences.
- The Short version is the worst place. 48.1% of its 206 sentences exceed 20 words. Elsewhere the share is 12.3%.
- You still had to ask. After 2026-11-10, five of your prompts added "short sentences" or "bullet pointing" [Ref7].

## 4. What the remaining long sentences are made of

The script counted features of the 581 sentences over 25 words [Ref6]. One sentence can have several features.

| Feature | Share of the 581 | What the skill says about it |
|---|---|---|
| A join | 57.1% | Rule 3 prescribes it |
| A colon inside the sentence | 49.9% | No rule |
| A parenthesis | 47.5% | Rules 6 and 8 ask for it |
| Three or more commas | 28.7% | No rule |
| One or more subordinating words | 21.3% | Rule 3 allows one clause |
| A trigger of the Rule 2 splitting test | 15.8% | "try to split" |
| Two or more subordinating words | 2.4% | The only form Rule 3 targets |
| None of these | 5.2% | |

I also read a random sample of 45 such sentences [Ref8]. I excluded 5 of them. Four were split errors of the script, and one was a quotation.

| What the sentence is | Count of 40 | Share |
|---|---|---|
| Two or more separate claims, joined | 15 | 37.5% |
| Two parallel items in one sentence | 9 | 22.5% |
| A list of three or more items in one sentence | 6 | 15.0% |
| A sequence of three or more actions in one sentence | 4 | 10.0% |
| One claim, long by its noun phrases or one parenthesis | 6 | 15.0% |

So 19 of 40 (47.5%) are a list or a sequence written as one sentence. Your two observations are one problem in these cases.

Three real examples follow.

- This sentence holds a list and has 45 words. Your prompt for that page had asked for short sentences and bullets.

  > The total is 230 to 310 GB/s above about 30 lines, 459 to 480 GB/s at 12 to 28 lines, and 543.9 to 549.0 GB/s (the highest measured) at 8 to 12 lines, and the rule inside the core that causes this is not established.

- This sentence holds a sequence and has 35 words. It is from a chat reply.

  > Then I fill the run ids into the description and the replies, edit the PR description, post the 26 thread replies and the combined reply as one review, comment on #5021, and re-request Isaac's review.

- This sentence joins two claims and has 26 words. It is from a chat reply.

  > Parts A, B and C are complete on CRB (the Arm server under test), and Part D (the steps that need administrator rights) was not run.

## 5. What the long paragraphs are made of

I read a random sample of 30 paragraphs with three or more sentences [Ref8]. I excluded one, the text of a flow diagram.

| What the paragraph is | Count of 29 | Share |
|---|---|---|
| Separate points, or aspects of one thing | 18 | 62% |
| A reasoning chain about one point | 7 | 24% |
| A sequence of steps or events | 2 | 7% |
| A "Short version" paragraph | 2 | 7% |

So 20 of 29 hold the two cases that you named: several perspectives, or a sequence.

Your reply to Codex adds a limit. Short, simple text can stay whole. So not all 20 need bullets.

## 6. Why the skill does not prevent them

Every quotation is from the skill file. Its reference entry lists the line numbers [Ref1].

### F1. Rule 3 names no number

- The rule says "Use short sentences" [Ref1]. It gives no word count.
- 13.0% of real sentences exceed 20 words.
- In the test the rule made no measurable difference: 7.4% without it, 6.3% with it (section 10).

### F2. Rule 3 targets a form that is now rare

- It asks to break "a sentence with several subordinate clauses" [Ref1]. The self-check allows one such clause [Ref1].
- Only 2.4% of the sentences over 25 words hold two or more subordinating words.
- So the rule cannot touch the other 97.6%.

### F3. Rule 3 prescribes the most common long form

- "If two clauses must stay together, join them with ", and" or ", or"" [Ref1].
- No test says when clauses must stay together.
- 57.1% of the sentences over 25 words contain a join.

### F4. The splitting test of Rule 2 is narrow

- It lists four phrases and the semicolon. It says "try to split it" [Ref1].
- 15.8% of the sentences over 25 words contain one of them.
- A colon is in 49.9%. No rule names the colon.

### F5. Rule 4 looks only at paragraphs

- "When one paragraph carries several separate points, break it into bullet points" [Ref1].
- 19 of 40 sampled long sentences are a list or a sequence inside one sentence.
- That case is outside the rule.

### F6. Rule 4 does not name your two cases

- Its only trigger is "several separate points". It names no perspectives, no sequence and no numbered list.
- 18 of 29 sampled paragraphs held separate points or aspects. 2 of 29 held a sequence.
- So the model must guess what "separate" means.

### F7. Rule 4 offers an alternative to bullets, and its check cannot fail

- "Otherwise separate sentence groups with a blank line" [Ref1]. The self-check accepts "bullets or a blank line" [Ref1].
- Every paragraph ends with a blank line. So every paragraph passes.
- No size limit exists for a paragraph or a bullet. 15.6% of report paragraphs exceed three sentences.

### F8. Rules 6 and 8 add parentheses without a size limit

- Rule 6 asks for "a clause saying what it means" [Ref1]. Rule 8 asks for "one clause in parentheses" [Ref1].
- 47.5% of the sentences over 25 words hold a parenthesis.
- 29.3% of them would be within 25 words without it.

### F9. Rule 7 limits the number of sentences, not their length

- "At most three sentences" [Ref1].
- 48.1% of the sentences in "Short version" blocks exceed 20 words.
- The summary is the first text you read.

### F10. Rules 3 and 4 have no example, and the self-check has nothing to count

- Rules 1, 2, 5 and 6 show Good and Bad examples. Rules 3 and 4 show none.
- Your PR-description skill sets a 2,000-word limit and gives the command that counts it [Ref11].
- Hypothesis: examples and a countable check each make a rule more effective. The test changed both at once. A test with one change at a time would separate them.

### F11. No rule says what to leave alone

- Rule 2 says "One claim per sentence" [Ref1]. It gives no case in which clauses may stay together.
- In the boundary task the current skill broke your cache sentence in 3 of 3 runs (section 10).
- In the same runs it left a 45-word sentence as prose in 2 of 3 runs.
- So the current rules split what is short and keep what is long.

### Smaller defects found during the inspection

| # | Defect | Where |
|---|---|---|
| S1 | A stale rule number. "Rule 1 applies only to terms imported from outside the code" must read "Rule 8". Rule 1 was "Define a term" before the renumbering [Ref3]. | Code comments |
| S2 | Four semicolons in the skill text. Rule 3 bans the semicolon. | Modes, Rule 8 (twice), self-check |
| S3 | Code comments get Rules 1 and 2 only. Rule 3 is not named. | Code comments |
| S4 | The Check-mode table asks for an "Original phrase". A defect of paragraph size has no phrase. | Check-mode output format |
| S5 | The bodies of Rules 3, 5 and 7 are paragraphs of three separate instructions. | Rules 3, 5 and 7 |

## 7. What is not the cause

- The skill text reaches the model. It is in the context of main sessions and subagents. 565 subagent transcripts carry Rule 3 [Ref5].
- The position in the file does not matter. The old order gave 8.1% long sentences in the test, and the current order gave 6.3%.
- The title word does not matter. "Prefer" and "Use" are part of that same comparison.

One point stays open.

- Long sentences in real chat fell from 25.5% to 12.8% on 2026-11-10.
- Hypothesis: the model change caused the fall, not the skill edit of that day.
- Insufficient data. The same test under Fable 5.1 would confirm it. One call to that model returned an API error on 2026-11-20.

## 8. Review of the Codex inspection

The Codex report has two versions. You answered the first one [Ref17]. The second one is the file that you asked me to review [Ref16].

### What I adopted

| Idea from the Codex report | Where it is now |
|---|---|
| A sentence with short, simple clauses stays whole. This is your own boundary. | Rules 2, 3 and 4 of the proposal, with your cache sentence |
| Bullets carry no category labels. | Rule 4 and the self-check |
| Examples come in pairs: one text to keep, one text to change. | Rules 2, 3 and 4 |
| A clause inside another clause is a defect at any length. | Rule 3 |
| A split must keep the meaning. | Rule 3 |
| A short sequence stays in prose. | Rule 4 |
| The final check asks whether the text was split too much. | Self-check |

### What I did not adopt

- Codex removed every word limit. Your reply did not ask for that. You called the first version "towards right direction" [Ref17].
  - That version aimed for 20 words. It asked for a review of every sentence over 25 words.
- Without a limit, long sentences stay. Codex's wording gave 11.8% in the test, and the current skill gave 6.3%.
- Its Rule 3 replaces yours and so drops the semicolon ban. 9 semicolons appeared in 519 sentences. The current skill gave none.
- Its Rule 2 says "Prefer one main point per sentence". Your Rule 2 calls a 15-word "Since" sentence Bad [Ref1]. I kept your Rule 2 unchanged.
- Its Rule 3 title says "Prefer short sentences". You replaced "Prefer" by "Use" in that title on 2026-11-10 [Ref3].
- Codex measured no output. Its report says so [Ref16].

### Where the two reports agree

Both reports found these three gaps independently.

- Rule 3 counts clauses, not length.
- The check for Rule 4 accepts a blank line.
- No rule covers a sequence.

One sentence in the second Codex version needs care. It says that word limits lacked evidence of your preference. That sentence is Codex's, and I did not find it in your reply [Ref17].

## 9. Proposed wording

The full proposed text is in one file [Ref12]. A diff against the current skill is next to it [Ref13].

The proposal follows one idea.

- Limits decide what is too long.
- Fixes say how to repair it.
- Text within the limits stays as it is.

| # | Change | Answers |
|---|---|---|
| 1 | Rule 3 gets limits. Over 25 words: always fix. 21 to 25 words: fix, unless the sentence makes one simple claim. 20 words or fewer: leave it alone when its clauses are short and simple. | F1, F2, F11 |
| 2 | Rule 3 gets four ordered fixes and two Good and Bad pairs. It bans a clause inside another clause. A split must keep the meaning. | F3, F4 |
| 3 | Rule 2 keeps your text. It gains one line and your cache sentence as a "Keep" example. | F11 |
| 4 | Rule 4 names three cases for a list and three cases for prose. Bullets start with their content, without labels. | F5, F6, F11 |
| 5 | Rule 4 sets sizes. A paragraph and a bullet have at most three sentences. The blank-line option is removed. | F7 |
| 6 | Rules 6 and 8 limit a parenthesis to 8 words. A longer one becomes its own sentence. | F8 |
| 7 | Rule 7: each Short version sentence obeys Rule 3. | F9 |
| 8 | The self-check counts. For a file it runs the checker. | F10 |
| 9 | Fixes for S1 to S5. | S1 to S5 |

The proposed text has 1,882 words. The current text has 1,038 words. So every session loads 844 more words.

## 10. Test of the wordings

### Design

- All runs used the model Fable 5.2.
- The context was your real `CLAUDE.md` plus one version of the skill text. Nothing else differed between versions.
- The Claude command line ran in its safe mode. That mode ignores the installed `CLAUDE.md`, skills, hooks and plugins. Tools were off.
- Four tasks used prompts in your usual style. None asks for short sentences or bullets.
  - T1: rewrite three passages that you once asked me to rewrite [Ref7].
  - T2: write a status report from raw benchmark notes.
  - T3: explain TLB misses and huge pages. A TLB is the processor's cache of address translations.
  - T4: rewrite 10 short passages. This is the boundary task [Ref18].
- Each version ran each of its tasks three times. Versions A and B did not run T4.
- The checker measured each reply.
- The test took 75 runs and cost 45.00 US dollars, as reported by the command line [Ref9].

| Code | Version of the skill text |
|---|---|
| A | The current text without Rules 3 and 4 |
| B | The text used until 2026-11-10 |
| C | The current text |
| X | The current text with the Rules 2 to 4, the examples and the checks that Codex suggests |
| D1 | My first proposal: a 20-word limit, every join split, labelled bullets |
| D2 | The revised proposal of section 9 |

### Sentence length, tasks T1 to T3

| Version | Sentences | Over 20 words | Range over the 9 runs | Longest | With a join | 6 words or fewer | Facts kept |
|---|---|---|---|---|---|---|---|
| A | 578 | 7.4% (43) | 3% to 13% | 41 words | 8.8% | 19.9% | 96 of 96 |
| B | 591 | 8.1% (48) | 4% to 12% | 37 words | 10.8% | 19.8% | 95 of 96 |
| C | 522 | 6.3% (33) | 2% to 14% | 36 words | 9.2% | 22.4% | 96 of 96 |
| X | 519 | 11.8% (61) | 5% to 24% | 43 words | 16.8% | 13.7% | 96 of 96 |
| D1 | 712 | 0.0% (0) | 0% to 0% | 19 words | 0.6% | 27.8% | 96 of 96 |
| D2 | 649 | 0.0% (0) | 0% to 0% | 20 words | 7.4% | 21.7% | 96 of 96 |

"Facts kept" counts 32 numbers and names from the sources of T1 and T2. The script checks that each one appears in the reply.

What the table says:

- The current Rules 3 and 4 show no effect on sentence length. A, B and C lie inside each other's range.
- Codex's wording did not reduce long sentences. Its share was the highest of the six versions.
- Both of my proposals removed long sentences in all 9 runs.
- My first proposal also removed the short joins. Under the current skill, 33 of the 48 joined sentences are within 20 words. The first proposal left 4 joins in 712 sentences.
- The revised proposal kept the short joins. All its 48 joined sentences are within 20 words.
- My first proposal wrote more very short sentences: 27.8% against 22.4%. The revised proposal wrote 21.7%.

### The boundary task, T4

Each cell counts the runs, out of 3, that gave the expected form.

| Passage | Expected form | C | D1 | X | D2 |
|---|---|---|---|---|---|
| 1. Your cache sentence, 14 words | stays one sentence | 0 | 0 | 3 | 3 |
| 2. Three developed sentences about the cache | list | 1 | 3 | 3 | 3 |
| 3. "Check the lease, start the run, then save the log." | stays one sentence | 0 | 0 | 3 | 3 |
| 4. A clause inside a clause, 18 words | two sentences | 3 | 3 | 3 | 3 |
| 5. Three values in one sentence of 45 words | list | 1 | 3 | 3 | 3 |
| 6. Five steps in one sentence of 35 words | numbered list | 3 | 3 | 3 | 3 |
| 7. Two claims and two parentheses, 26 words | two or more sentences | 2 | 1 | 3 | 3 |
| 9. "The host has 64 physical cores, so it was nearly idle." | stays one sentence | 0 | 0 | 3 | 3 |
| 10. Three short sentences: done, not done, checked | list | 2 | 3 | 0 | 0 |
| Expected form, of 27 | | 12 | 16 | 24 | 24 |
| List items with an added label | | 1 | 22 | 0 | 0 |

Passage 8 is a short "because" sentence. I only recorded it.

- C and D1 split it in 3 of 3 runs.
- X and D2 kept it whole in 3 of 3 runs.

What the table says:

- The current skill splits what is short. It turned your cache sentence into a list twice and into three sentences once.
- My first proposal broke your boundary in every run. It also added 22 labels, such as "Benefit:" and "Done:".
- Codex's wording and the revised proposal gave the expected form in 24 of 27 cases. Neither added a label.
- Both keep passage 10 as a paragraph. I had expected a list there (decision 2).
- The revised proposal writes fewer sentences. In this task the current skill wrote 194 sentences in 3 runs. The revised proposal wrote 146.

```
Two goals, four versions

                    long sentences    boundary passages
                    (T1 to T3)        in expected form (T4)
C  current skill    6.3%              12 of 27
X  Codex wording    11.8%             24 of 27
D1 first proposal   0.0%              16 of 27
D2 revised          0.0%              24 of 27
```

Only the revised proposal reaches both goals.

### Side effects of the revised proposal

These numbers compare D2 with the current skill on T1 to T3.

- It used 18,556 output tokens per run against 12,139. That is 53% more. The count includes the model's thinking.
- It took 175 s per run against 118 s. That is 48% more.
- It wrote 1,054 visible words per run against 955. That is 10% more.

### What the test does not show

- No version wrote many long paragraphs. The counts over three sentences were 0 to 5 per version. So the paragraph limit is not tested.
  - Insufficient data. A week of real sessions with the proposed text would show it. Then rerun `corpus_stats.py` [Ref6].
- The test is one prompt and one reply. Real sessions are long. The current skill gives 6.3% in the test and 12.8% in real chat.
- The model never wrote a sentence of 21 to 25 words under the revised proposal. So that part of Rule 3 is not tested.
- The test replies are Markdown, not HTML.
- Only Fable 5.2 ran.

## 11. Decisions for you

My recommendation: adopt the revised proposal. Then measure one week of real sessions.

1. Decide the limits. The proposal uses 25 words as the hard limit and 20 words as the point below which nothing is forced.
   - GOV.UK, the website of the UK government, asks its writers to split sentences over 25 words [Ref14].
   - The Plain English Campaign recommends an average of 15 to 20 words [Ref15].
   - Today 5.6% of your sentences exceed 25 words, and 13.0% exceed 20 words.
2. Decide passage 10. The revised proposal keeps three short sentences on three aspects as one paragraph. If you want bullets there, Rule 4 needs a firmer trigger.
3. Decide short "because" sentences. The revised proposal keeps them whole. Your Rule 2 lists "because" as a place to try a split.
4. Decide the sizes. The proposal allows three sentences per paragraph and per bullet.
5. Decide code comments. The proposal applies Rule 3 to them. The current text does not say.
6. Decide the checker. The proposed self-check names a script path inside the skill folder. The script is not installed there [Ref10].
7. Weigh the cost. The proposal adds 844 words to every session. It used 53% more output tokens in the test.

## 12. Limits of this inspection

- My script skipped text inside code fences. I corrected this for the rewrite tasks T1 and T4. In real outputs, rewritten text inside a fence is still not counted.
- That correction changed numbers of the first version of this report. One example: the current skill went from 6.7% to 6.3%.
- The first script version failed to split 4 of 45 sampled long sentences. The final version splits before a lower-case code name. I did not redraw the sample.
- The script reads a chart legend in a plain `div` as a paragraph. I saw several such cases.
- The sample labels in sections 4 and 5 are my own judgment. Nobody checked them.
- The expected forms of the boundary task are my reading of your two messages. Passage 1 is your own example. The others are not.
- The script counts subordinating words, not clauses. It does not count "that".
- The real outputs cover 10 days, 2026-11-10 to 2026-11-20.
- The 12 report files are those last changed after 2026-11-15 14:51 PST. One file holds 24,468 of their 50,572 words.
- This report passes the proposed limits. The checker reports its longest sentence at 20 words.

## References

- [Ref1] `~/.claude/skills/plain-english/SKILL.md`, 120 lines, changed 2026-11-15 14:51 PST. Lines cited:
  - Rule 2: title 28, Bad example 33, splitting test 35.
  - Rule 3: title 37, body 39.
  - Rule 4: body 43.
  - Rule 5: body 47. Rule 6: body 54.
  - Rule 7: body 65. Rule 8: opening 71.
  - Code comments: 93 and 95. Check-mode table: 104.
  - Self-check: paragraphs 115, subordinate clauses 116.
  - Semicolons: 15, 80, 87, 119.
- [Ref2] Earliest session transcript that carries the skill text: `~/.claude/projects/-home-jhan-workspace-random/48fcc58b-9996-44ad-adc4-9498fb73c992.jsonl`, 2026-09-11. It holds "Rule 7 - Use bullet points and blank lines to separate points" and "Rule 8 - Prefer short sentences".
- [Ref3] Skill text as it stood until 2026-11-10: `~/workspace/ai-runs/plain-english-inspection-20261120/data/skill_body_before_2026-11-10.md`.
  - Taken from a transcript of 2026-11-09 17:02 UTC.
  - Last seen in a context at 2026-11-10 04:25 UTC.
  - The current rule order was first seen at 2026-11-10 15:54 UTC.
- [Ref4] Model names in the transcripts, from `data/corpus_stats.txt` in the folder of [Ref3].
  - `claude-fable-5-1`: all 1,271 chat replies before 2026-11-10 04:25 UTC.
  - `claude-fable-5-2`: all 766 chat replies after 2026-11-10 15:54 UTC.
- [Ref5] `grep -rl "Rule 3 - Use short sentences" ~/.claude/projects`: 595 transcripts, of which 565 are subagent transcripts. Run on 2026-11-20.
- [Ref6] `~/workspace/ai-runs/plain-english-inspection-20261120/scripts/corpus_stats.py`. Output: `data/corpus_stats.txt`. Input: `data/chat_all.jsonl`, made by `scripts/extract_chat.py`, and the 12 report files listed in the script.
- [Ref7] `~/.claude/history.jsonl`. Prompts of 2026-11-11 20:10, 2026-11-12 10:07, 2026-11-15 08:40, 2026-11-15 14:47 and 2026-11-20 09:20 PST. The passages of task T1 come from prompts of 2026-09-15, 2026-11-03 and 2026-11-08.
- [Ref8] `data/manual_labels_sentences.tsv` and `data/manual_labels_paragraphs.tsv` in the folder of [Ref3]. Random seed 20261120.
- [Ref9] `~/workspace/ai-runs/plain-english-inspection-20261120/experiment/`.
  - `ctx/`: the seven contexts.
  - `prompts/`: the four tasks.
  - `out/`: the 75 replies.
  - `run_one.sh`: the command of one run.
  - Results: `data/experiment_stats.txt`, made by `scripts/analyze_experiment.py`.
  - File names use NONE, OLD, CUR, CODEX, NEW2 and V3 for versions A, B, C, X, D1 and D2. NEW is an earlier draft of D1.
- [Ref10] `~/workspace/ai-runs/plain-english-inspection-20261120/proposed/scripts/check_lengths.py`.
- [Ref11] `~/.claude/skills/PR-description/SKILL.md`, lines 31 and 99 to 103.
- [Ref12] `~/workspace/ai-runs/plain-english-inspection-20261120/proposed/SKILL.md`. My first proposal is `SKILL.v2.md` in the same folder.
- [Ref13] `~/workspace/ai-runs/plain-english-inspection-20261120/proposed/SKILL.diff`.
- [Ref14] GOV.UK, "Clear language": https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/ . Wording as returned by a web search on 2026-11-20. I did not open the page.
- [Ref15] Plain English Campaign, "How to write in plain English": https://www.plainenglish.co.uk/how-to-write-in-plain-english . Wording as returned by a web search on 2026-11-20. I did not open the page.
- [Ref16] `~/workspace/random/plain-english-inspection-codex.md`, second version, changed 2026-11-20 09:50 PST.
- [Ref17] Codex session record: `~/codex-home-claude-agentsrv/sessions/2026/11/20/rollout-2026-11-20T09-34-18-01a1fa05-fbbe-7743-8c68-a298b612d8d1.jsonl`.
  - It holds the first version of the Codex report, written at 09:35 PST.
  - It holds your reply of 09:50 PST with the cache sentence.
- [Ref18] The boundary task, in the folder of [Ref3] and [Ref9].
  - Task: `experiment/prompts/T4_boundary.txt`.
  - Scoring: `scripts/score_boundary.py`.
  - Output: `data/boundary_stats.txt`.
