## Short version: purpose

`render.sh` runs the test of the Part A analysis and keeps the three result pages that this test builds, two from invented data and one from an empty result folder. Then it takes one screenshot of each page with a headless Chrome for which every host name is unknown, and it cuts each screenshot into pieces of at most 1500 px height. It measures nothing: its output is pictures of the three test pages.

## Words used here

- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Part A analysis**: the scripts that analyse Part A of the test plan of 2026-11-13 and build its result page. They lie in the folder `new-test-kernel/partA-analysis` of the code.
- **`test_partA.py`**: the test of the Part A analysis. It builds result folders with invented rates, runs the analysis on them and checks the computed values.
- **Synthetic page**: a result page that `test_partA.py` builds from its own test input. It shows a banner that says that every rate on it is invented.
- **Set**: one of the three cases of that test. The folders `set1` and `set2` hold invented data, and `set3` holds an empty result folder.
- **Headless Chrome**: the browser Chrome in a mode without a window. It can load a page and save a picture of it.
- **Screenshot**: a picture of the browser window, saved as a file in the format PNG.
- **Profile folder**: the folder in which Chrome keeps the settings and the data of one user.
- **Here-document**: lines of a shell script that the shell passes to a command as its standard input.
- **px**: pixel, one point of a picture.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. The script sets the stop at a failed command and three paths: the scratch folder, its sub-folder `render` and the Chrome program ({L3-5}).
2. It runs `test_partA.py` with `--keep`. The three synthetic pages then stay in the folder `partA-synthetic` ({L6}).
3. It deletes the old screenshots ({L7}).
4. For each of the three pages it starts Chrome with an empty profile, a nearly empty environment and no host name lookup, and saves one screenshot of a window of 1000 px width ({L8-9}).
5. A Python program finds the height of the content in each screenshot and cuts the picture into pieces of at most 1500 px height ({L10-20}).

## Behavior a reader must know

- All paths are fixed paths of the agent server. `S` names the first place of this code, the scratch folder `bwx-2026-11-13` of the project, not the folder of the code repo ({L4}).
- A failed test does not stop the script. The exit status of the pipeline of {L6} is that of `tail`. The script then goes on to the screenshots, with the pages that the test wrote before it failed.
- A failed run of Chrome stops the script: `set -e` is on ({L3}, {L9}). A failed Python program at the end gives the script a failed exit status too.
- The script deletes three things: the folder `partA-synthetic`, through the option `--keep` of the test ({L6}), the old screenshots ({L7}) and the profile folder of Chrome ({L8}).
- The script makes only the profile folder. It does not make the home folder, the temporary folder or the font settings file that {L9} names inside `render`.
- The screenshot is taken of a window that is 15500 px high unless the variable `H` gives another height. The Python program then cuts off the empty rest below the content ({L9}, {L15}).
- The search for the content height expects a nearly white page background ({L15}).
- The Python program needs the libraries Pillow and `numpy`.
