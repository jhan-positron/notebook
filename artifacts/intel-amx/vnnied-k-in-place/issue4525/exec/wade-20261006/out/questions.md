14. Dead symbol: which line at HEAD, other than its own declaration, reads, calls, includes or compiles this, and if none does, what is it in the PR for?
15. Added prose line: does it hold a word neither the dictionary nor the code knows, a name one letter from a real symbol, or an over-wide Markdown line?
13. Number or constant: can a reader say what this number measures, from a name in reach, a derivation comment or the stem alone, and why did any former name leave?
16. Debug switch, dump, include or trace: is it meant to ship enabled in the target branch, and under which guard the file already uses should it sit?
17. Comment or label: does every identifier, placeholder, path, label, tense and negation in it match the code line it describes at HEAD?
18. Existing helper: does a function at HEAD or on the base branch already compute, decide, wait for or order this, with no difference the output depends on?
19. Declaration types: can this value be negative or change after startup, and does the surrounding code already use the unsigned, const or initialized form at HEAD?
20. Identifier: at the use site, does the name say what it holds and match its comment, siblings and repository spelling?
21. Declaration: can a reader of this file alone at HEAD learn what the new parameter, variable, routine, helper, default or term is for and why it has this shape?
22. Redundant code: if this statement, member, branch, specifier or scope were deleted, would any state, type or build change, or does the language or nearby code already give it?
23. Disabled code: does any build compile this `#if 0` block or commented-out statement, and if not, why is it kept rather than deleted or marked as reference?
24. Placement: does a reader find this declaration, constant, include or helper in the file whose name owns it, or must they search a file about something else?
25. Silent behavior change: on which input do the removed line and the added line behave differently, and does the PR body say that difference is intended?
26. Count, index or wait set: on every path, does this count, index or completion wait cover exactly the set it stands for, and who reads the result otherwise?
27. Silent fallback: can a bug-free caller reach this clamp, early return or spin, and if not, why is it not an assert that names the value?
28. Shared state: what protects mutation, which thread writes, which reads at HEAD, and does the lock, atomic or wait live in the object that owns the state?
29. Buffer: after the line that frees, submits or reallocates it, who still reads it, and does its declared alignment reach the consumer's widest aligned store?
30. Hot path: does every call on a spin, layer, token or poll path do work the sibling or BASE avoided, unneeded in the common case?
31. State ownership: who owns this record, does every call into the subsystem sit under its guard, and does the row key name one thread in every forward?
32. Operator view: can an operator see, measure or switch on the new state, counter, trace or option through the debug dump, Perfetto, FUSE or the launcher?
1. Value row, fixture literal or opaque literal: name what depends on this exact value (reader, exercised field read) or where it came from (command, date, revision).
2. Compile-time shape check: which production line outside the probed type's own header would misbehave if it flipped, and is it not already fixed by a declaration or static_assert in a header?
3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, without hardware, on a second run?
3B. Named run: which run, by binary or command, build configuration and commit, executed the changed path at this head, and where does the PR say so?
4. Duplicate coverage: which deliberate code break fails test A but passes test B, and, for a new test binary, which existing binary already executes the function under test?
5. Test label: next to the setup, the REQUIRE lines and the sibling units, does the name, tag string or result print describe the passing state and follow the siblings' pattern?
33. Changed path: which test enters the changed code at its production entry, and which assertion fails if that code is wrong?
34. Workaround: is this workaround temporary or permanent, and if temporary, which story tracks the root cause and where is the TODO that says so?
6. Claim sentence: for every subject it covers (each type, path, element count, build path), which code line reaches what it says, and does it say where it stops?
7. CI sentence: which lanes set or omit this setting, with their triggers, and does the sentence name the lane it means?
8. Result row, body sentence, branch: do the result ids, the sentences the review-round commits touched, the merge state, a ported file and the reviewer's open suggestions all match this head?
9. Body passage, comment or Note: would deleting it change a decision about the head, or cost a reader with only the code a fact the code must honor?
10. Hunk, file row, removed comment or flag: reverted alone, would any body sentence stop being true or any PR symbol stop compiling, and can the author say where it came from?
11. Commit: does it exist only because an earlier commit of this PR was wrong or badly worded?
12. Shared-header hunk no test observes: has an owner of the file accepted the placement, in writing, at a head that contains it?
35. Bot finding: which HEAD line (initializer, caller, or PR title) decides the claim, does it agree with the bot, and is it quoted?
