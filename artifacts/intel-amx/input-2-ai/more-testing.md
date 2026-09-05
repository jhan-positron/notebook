We need to expand test coverage of AMX change.

# MMLU Pro
Nightly CI tests MMLU Pro, I do not know what it is, but hopefully you can figure out how to run it. 

# SOAK
I am advised to run SOAK testing, again I cannot give you a pointer, please find out and run it.

# CI 
We have been running runtron, now we need to test AMX change using same tests as CI do.

# models
We need to run at least 4 models, 3 models we saw AMX boost and gpt-oss for regression testing.

Please also pick some models and TP and users from CI, so we can compare with CI.

# output
Generate status report md files at PR3879/more-testing/ folder, create it if not existing.

First, please generate a test plan md file at PR3879/more-testing/, and then proceed with the plan.

We will iterate the testing, please create sub folders for each round (today is round 1).

Please keep updating status report md file: whenever a test result is out for one model, add to the file.


