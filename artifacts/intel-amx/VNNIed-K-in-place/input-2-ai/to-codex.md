Let's build a new solution on top of PR3879: make K VNNI layout at its generation.

PR3879 is AMX baseline solution. It does not change K layout and has to pay the panalties such
as an extra transposing of the score matrix. 

This project saves the K cache to VNNI layout directly, and we expect AMX perf boost will be
better leveraged than baseline. We realize that AVX path will be updated because of this.

We will need to measure both TPS and TTFT.

# output
Generate design doc, design/codex-VNNIed-K.html.

# Bill's input
After you complete design, 
please check out Bill's slack message, https://positronai.slack.com/archives/D0AVD4EG675/p1789087593574419,
he offered his investigation.

Add a section to design doc:
- anything we can learn from Bill's investigation?
- any problems do you see Bill's investigation?


# Comment claude design, implementation and tests
Claude code is working on the same problem and will generate the following:
- design doc: design/claude-VNNIed-K.html
- implementation: workspace is ./tron-VNNIed-K, branch is jhan-amx-vnniK
- test report: status/Monday-morning-report.html


Generate design/codex-review-claude.html:
- review claude design
- review claude test data

claude will do the design, implementation and testing over several hours, please start a monitor to track
claude's deliveries.
