# Candidate rules for the section "How to review this PR"

Each version is one rule a writer follows to produce the section. Each is under 100 words.

## V1 Risk first

Name the two or three places where this PR could be wrong in a way that is hard to see: a pointer or value that crosses a boundary, a path selection, a type that must not leak. For each, state the question the reviewer must answer, the files to read, and the test that pins the answer. Leave out anything a test or a code comment already settles. Do not list the remaining files.

## V2 Decisions first

List the decisions in this PR that a reviewer could reasonably make differently: a name, an abstraction boundary, a default, a tolerance, a contract. For each, state the choice, the alternative considered, and where the reviewer can check the consequence. Two to four items. The rest of the diff follows from these decisions and needs no guidance.

## V3 Production effect first

Answer three questions, in order. What changes for a shipped binary, and under which setting? How is it switched off, and what does the switch restore? Which files carry that behaviour? For each answer, point at the files and at the test or measurement that proves it. Nothing else goes in this section.

## V4 Invariants first

State the properties this PR promises and later work relies on, one sentence each. For each property, say where it is enforced: a type, an assertion, a compile check, or a test. The reviewer then checks the enforcement, not the prose. Three items at most. A property with no enforcement point is an open item, not a review thread.

## V5 Follow one value

Pick the one value whose path this PR changes and follow it in order: who writes it, who reads it, who copies it, who moves it to the device. At each step, name the function and the question to check there. A reviewer who follows the path has read every line that matters. The rest of the diff is support for these steps.

## V6 Where the evidence stops

For each claim the PR relies on, name what proves it (a test, a measurement, a compile check) and what does not: the case a test cannot detect, the configuration CI does not build, the host not measured. The reviewer decides whether each gap is acceptable. List the gaps, not the proofs.

## V7 Strongest objection

Write the best case against merging this PR in two or three points, each with the place a reviewer would check it. If an objection is answered, name the measurement or test that answers it. If it is open, say so and name who decides. A reviewer who cannot add to this list can approve.

## V8 Risk and decisions (combined)

Two lists of at most three items each. First, where the PR could be wrong in a way that is hard to see: for each, the question, the files to read, and the test that pins it. Second, the choices a reviewer might make differently: for each, the choice and the alternative. Omit everything the tests already settle.
