# context
Ben made 3 comments at PR #4424, #2 and #3 are about same thing: abstract VNNI-K and native K and VNNI-V data model,
so that the main function code accesses some higher level abstraction tensor data types. This change is not directly  
related to AMX feature as targeted by #4424, but it is a good optimization.

# understand his points
He commented at his #3 comment, he has some reservation about the interfaces from claude. He seemed saying layout
and view can be combined. Claude designed the abstration separation as:
layout --> storage --> view, so I guess his point is, layout itself should be view of which it is how storage are
presented to client. I tend to agree with his point, assuming my understanding is right. 

# action plan
1. Check out his comments, and confirm #1 is separate from #2 and #3
2. Synthesize claude design and Ben's comments #2 and #3, and confirm if my understanding is right or wrong
3. If you disagree with Ben's suggestion, or if you need more info from him, stop here, and elaborate your questions
4. Before this PR, V cache are already VNNI layout. So we can say, Ben's suggestion is independent from this PR.
   Given that, we'd spin out a new PR which introduces the new abstraction on VNNI-V and native K. And then we
   update PR #4424 to be atop the new PR (this means the VNNI-K change as introduced in PR #4424 will be a local 
   change within the new tensor data type, not at main function). If you agree with this thought, generate a github 
   issue, assign the issue to me and work out the software design to address the newly created issue.

# output
If you stop at #3, generate your output from step 1 through 3 to status/evaluate-Ben-suggestion-new-tensor-type.html.
Otherwise:
- Create the github issue as described, let's say it is issue #6000
- Create issue6000/, the following output are at this folder
- Generate output from action plan to status/design-new-tensor-type.html
-- Another agent will implement the design by reading this file
