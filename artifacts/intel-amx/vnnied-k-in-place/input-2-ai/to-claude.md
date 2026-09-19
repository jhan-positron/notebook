Let's build a new solution on top of PR3879: make K VNNI layout at its generation.

PR3879 is AMX baseline solution. It does not change K layout and has to pay the panalties such
as an extra transposing of the score matrix. 

This project saves the K cache to VNNI layout directly, and we expect AMX perf boost will be
better leveraged than baseline. We realize that AVX path will be updated because of this.

We will need to measure both TPS and TTFT.

# output
Generate design doc, design/claude-VNNIed-K.html.

Generate implementation (code changes, make changes, new unit tests) based on branch jhan-amx-p0,
the workspace is ./tron-VNNIed-K, branch is jhan-amx-vnniK.

Test on delphi-3bda after CI window, measure TPS and TTFT of kwen3-4b, AMX off, AMX baseline and VNNIed-K.
Prompt length: 1k/2k/8k.

Generate status/Monday-morning-report.html, include raw test data description for another agent to 
review..


# Bill's input
After you complete design, coding, and while you are waiting for 3bda (do not do the following before that),
please check out Bill's slack message, https://positronai.slack.com/archives/D0AVD4EG675/p1789087593574419,
he offered his investigation.

Add a section to Monday-morning-report.html:
- anything we can learn from Bill's investigation?
- do we see similar perf results in our testing?

