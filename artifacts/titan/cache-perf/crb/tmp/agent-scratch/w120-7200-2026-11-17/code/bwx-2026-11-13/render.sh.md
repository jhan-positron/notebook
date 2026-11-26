# `render.sh` explained, line by line

- Source file: `bwx-2026-11-13/render.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 20 lines, 1577 bytes).
- sha256 of the source when this page was built: `070fa2cf338b600844aec0a5cfb5709e1d4219f665c0b8a710dba81155a7eef8`.

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

1. The script sets the stop at a failed command and three paths: the scratch folder, its sub-folder `render` and the Chrome program (lines 3 to 5).
2. It runs `test_partA.py` with `--keep`. The three synthetic pages then stay in the folder `partA-synthetic` (line 6).
3. It deletes the old screenshots (line 7).
4. For each of the three pages it starts Chrome with an empty profile, a nearly empty environment and no host name lookup, and saves one screenshot of a window of 1000 px width (lines 8 to 9).
5. A Python program finds the height of the content in each screenshot and cuts the picture into pieces of at most 1500 px height (lines 10 to 20).

## Behavior a reader must know

- All paths are fixed paths of the agent server. `S` names the first place of this code, the scratch folder `bwx-2026-11-13` of the project, not the folder of the code repo (line 4).
- A failed test does not stop the script. The exit status of the pipeline of line 6 is that of `tail`. The script then goes on to the screenshots, with the pages that the test wrote before it failed.
- A failed run of Chrome stops the script: `set -e` is on (line 3, line 9). A failed Python program at the end gives the script a failed exit status too.
- The script deletes three things: the folder `partA-synthetic`, through the option `--keep` of the test (line 6), the old screenshots (line 7) and the profile folder of Chrome (line 8).
- The script makes only the profile folder. It does not make the home folder, the temporary folder or the font settings file that line 9 names inside `render`.
- The screenshot is taken of a window that is 15500 px high unless the variable `H` gives another height. The Python program then cuts off the empty rest below the content (line 9, line 15).
- The search for the content height expects a nearly white page background (line 15).
- The Python program needs the libraries Pillow and `numpy`.

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/render.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (20 lines, 1577 bytes, sha256 `070fa2cf338b600844aec0a5cfb5709e1d4219f665c0b8a710dba81155a7eef8`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# render.sh: test, then screenshots of the three synthetic pages with the headless Chrome of the development machine (network blocked)` | Comment: the purpose. The script runs a test and then takes screenshots of the three synthetic pages with the headless Chrome of the development machine, with the network blocked. A synthetic page is built from invented data. Headless means that the browser opens no window. The development machine is the agent server. |
| 3 | `set -e` | `set -e`: the script stops when a command fails. Two cases do not stop it: a failed command before `&&`, and a failed stage of a pipeline that is not its last stage (line 6). |
| 4 | `S=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13; A=$S/render` | `S`: the scratch folder of this code on the agent server. `A`: its sub-folder `render`, where the screenshots and the files of Chrome go. The `;` divides the two commands. |
| 5 | `B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell` | `B`: the path of the headless Chrome program. It lies in the cache folder of the browser test tool Playwright, in the home folder of the user. |
| 6 | `cd /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partA-analysis && python3 test_partA.py --keep $S/partA-synthetic \| tail -1` | Changes to the folder of the Part A analysis. `&&` runs the next command only when the change worked. That command starts `test_partA.py` with `--keep` and the folder `partA-synthetic` below `S`. With `--keep` the test first deletes and makes that folder. Then it writes three sets there and leaves them: `set1` and `set2` with invented data, and `set3` with an empty result folder. Each set gets a page `partA-result.html`. `\| tail -1` shows only the last line of the output of the test. The exit status of a pipeline is that of its last stage, here `tail`. So a failed test does not stop the script. |
| 7 | `rm -f $A/set*.png` | Deletes the old screenshots: every file in `A` whose name starts with `set` and ends with `.png`. `-f`: it is no error when no such file exists. |
| 8 | `for n in 1 2 3; do rm -rf $A/profile; mkdir -p $A/profile` | Loop over the numbers 1, 2 and 3 of the sets. For each set it first deletes the profile folder of Chrome with all its content (`rm -rf`) and makes it again. `mkdir -p` also makes missing folders above it and accepts a folder that exists. So each run of Chrome starts with an empty profile. |
| 9 | `env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=1000,${H:-15500} --screenshot=$A/set$n.png "file://$S/partA-synthetic/set$n/partA-result.html" >/dev/null 2>&1; done` | One run of Chrome per set. `env -i` starts it with an empty environment plus these variables: the search path `/usr/bin:/bin`, a home folder, two folders for settings and cache files, a temporary folder (all inside `A`) and the font settings file `fonts.conf`. `timeout 120` ends Chrome when it still runs after 120 s. `--headless`: no window. `--no-sandbox`: Chrome does not isolate its helper processes. Nine options turn off parts that a screenshot does not need: the graphics hardware, shared memory in `/dev/shm`, the tasks of a first start, network use in the background, component updates, the sync with an account, extensions, and crash reports (two options). `--host-resolver-rules="MAP * ~NOTFOUND"` makes every host name unknown. The comment of line 2 calls this a blocked network. `--user-data-dir`: the profile folder of line 8. `--hide-scrollbars`: no scroll bars in the picture. `--window-size=1000,${H:-15500}`: a window of 1000 px width and of the height `H`, or of 15500 px when `H` is not set or empty. `--screenshot` writes a picture of the window to `set1.png`, `set2.png` or `set3.png` in `A`. The last argument is the page of the set as a `file://` address. `>/dev/null 2>&1` drops the output and the error output of Chrome. `done` ends the loop of line 8. |
| 10 | `python3 - <<P` | `python3 -` runs a Python program that it reads from its standard input. `<<P` gives the lines up to the line `P` (line 20) as that input. This is called a here-document. The word `P` is not quoted, so the shell first replaces `$A` in these lines with the path of the folder. |
| 11 | `from PIL import Image` | Python: takes `Image` from the picture library Pillow, whose module name is `PIL`. |
| 12 | `import numpy as np` | Python: loads the library `numpy` for arrays of numbers. |
| 13 | `for n in (1,2,3):` | Python: loop over the three sets. |
| 14 | `    im=Image.open('$A/set%d.png'%n).convert('RGB'); a=np.asarray(im)` | Python: opens the screenshot of the set and converts it to three colour values per pixel: red, green and blue. `a` is the picture as an array with one row per pixel row. |
| 15 | `    rows=np.where((a<250).any(axis=(1,2)))[0]; h=min(int(rows.max())+20, im.size[1])` | Python: `rows` holds the numbers of the pixel rows in which at least one colour value is below 250. Such a row holds something that is darker than a nearly white background. `h` is the last such row plus 20 px, and at most the height of the picture. So `h` is the height of the content of the page. |
| 16 | `    k=0` | Python: `k` counts the pieces. It starts at 0. |
| 17 | `    for y in range(0,h,1500):` | Python: loop over the top edges of the pieces: 0, 1500, 3000 px and so on, below `h`. |
| 18 | `        im.crop((0,y,1000,min(y+1500,h))).save('$A/set%d-%02d.png'%(n,k)); k+=1` | Python: cuts one piece of 1000 px width out of the picture, from `y` to 1500 px below it, and never past `h`. It saves the piece in `A` under a name such as `set1-00.png` or `set1-01.png`. Then it counts the piece. |
| 19 | `    print(n, 'content height', h, 'pieces', k)` | Python: prints the number of the set, the height of the content in px and the number of pieces. |
| 20 | `P` | Ends the here-document of line 10. The Python program runs with these lines. |
