# `render_q1.sh` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/render_q1.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 19 lines, 1564 bytes).
- sha256 of the source when this page was built: `968543d080c2f0fa92c44bb32f05f5203b3dc13b105bb58a8b75fa69b4e80828`.

## Short version: purpose

`render_q1.sh` takes a screenshot of an HTML page with a headless Chrome browser on the agent server and cuts it into pieces of 1500 px height. The browser runs with an empty environment and cannot find any host name, so the page is drawn without the network. The name refers to the result page of question Q1, but the script accepts any page.

## Words used here

- **Agent server**: the Linux server from which the tests were started and on which the analysis ran. The comment of the script calls it the development machine.
- **Headless Chrome**: a Chrome browser that runs without a window. It can draw a page into a picture file.
- **Screenshot**: the picture of the browser window. Here it is 1000 px wide and as high as the window.
- **Result page of Q1**: the HTML page with the results of question Q1 of the test plan of 2026-11-13, the question about one thread with an 8 MiB buffer. The script `make_q1_html.py` of the same folder builds it.
- **Environment**: the set of variables that a program gets from the program that starts it.
- **Profile folder**: the folder in which the browser keeps its own data.
- **Font settings file**: the file `fonts.conf`. It tells the browser where the fonts lie and which font to use for a font name [Ref2].
- **Here-document**: lines of a shell script that the shell gives to a command as its input. `<<P` starts them, and a line that holds only `P` ends them.
- **Pillow, NumPy**: two Python libraries. Pillow reads and writes pictures. NumPy works on arrays of numbers.
- **px**: pixel, one dot of a picture.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. The script stops at the first failed command from here on (line 4).
2. It turns the two arguments into full paths and creates the output folder (line 5).
3. It sets the path of the folder that holds the font settings, and the path of the browser (lines 6 to 7).
4. It deletes the profile folder and the pictures of an earlier call, and creates the folders that the browser needs (line 8).
5. It runs the browser, which writes the screenshot `page.png` (line 9).
6. A Python program finds the height of the content, cuts the screenshot into pieces of 1500 px, and prints the heights and the number of pieces (lines 10 to 19).

## Behavior a reader must know

- The script deletes files: the folder `profile` and every `page*.png` of the output folder (line 8). An older `page.png` and its pieces are replaced.
- The screenshot shows only the window, 1000 px wide and 16000 px high unless the variable `H` gives another height [Ref4]. A longer page is cut at the lower edge. The printed line gives both heights (line 18).
- The page is drawn without the network: every host name is unknown to the browser (line 9). A page that needs a file from another server is drawn without it.
- The fonts come from the font settings file of the folder `A`. That file maps the font names `system-ui` and `monospace` to the fonts DejaVu Sans and DejaVu Sans Mono [Ref2]. So the text of the screenshot can have other widths than in the browser of a reader.
- With `set -e` the Python part does not run when the browser fails or is ended by `timeout` after 180 s. The exit status of the script is then that of the failed command.
- The paths of the browser and of the font settings are fixed to the agent server (lines 6 to 7). On another machine the script needs other paths.
- The value of `OUT` stands without quotes in the browser command (line 9). An output path with a space would break that command.
- The comment in line 3 calls the command the same as in `render.sh`. Apart from the paths, two values differ: the time limit and the default window height [Ref1]. The older script keeps the profile folder, the home folder and the folder for temporary files in its own folder `render`. This script keeps them in the output folder.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/render_q1.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (19 lines, 1564 bytes, sha256 `968543d080c2f0fa92c44bb32f05f5203b3dc13b105bb58a8b75fa69b4e80828`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# render_q1.sh PAGE.html OUTDIR: screenshot of the page with the headless Chrome of the development machine (network blocked),` | Comment: the usage. The script takes two arguments: an HTML page and an output folder. It takes a screenshot of the page with the headless Chrome of the development machine, a Chrome browser that runs without a window. The network is blocked for the browser. |
| 3 | `# cut into pieces of 1500 px. Same command as tmp/agent-scratch/bwx-2026-11-13/render.sh.` | Comment: the screenshot is cut into pieces of 1500 px height. The comment says that the command is the same as in the script `render.sh` of the folder `bwx-2026-11-13`. Apart from the paths of their folders and files, the two Chrome commands differ in two values: the time limit is 180 s here and 120 s there, and the default window height is 16000 px here and 15500 px there. |
| 4 | `set -e` | `set -e`: the script stops as soon as a command ends with an exit status other than 0. |
| 5 | `PAGE=$(realpath "$1"); OUT=$(realpath -m "$2"); mkdir -p "$OUT"` | Three commands. `PAGE`: the full path of the first argument, the page (`realpath`). `OUT`: the full path of the second argument, the output folder. With `-m`, `realpath` also accepts a path that does not exist yet. `mkdir -p` creates the output folder with its parent folders, and gives no error when it exists. |
| 6 | `A=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/render` | `A`: the folder `render` on the agent server, in which the older screenshot script `render.sh` keeps its files. This script uses only the font settings file in it (line 9). |
| 7 | `B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell` | `B`: the path of the headless Chrome program on the agent server. It lies in the download folder of the browser test tool Playwright. |
| 8 | `rm -rf "$OUT/profile" "$OUT"/page*.png; mkdir -p "$OUT/profile" "$OUT/home" "$OUT/tmp"` | Two commands. `rm -rf` deletes the browser profile folder of an earlier call and every file of the output folder whose name starts with `page` and ends with `.png`. `-r` deletes a folder with its content, and `-f` gives no error for a missing file. `mkdir -p` then creates three folders in the output folder: `profile`, `home` and `tmp`. |
| 9 | `env -i PATH=/usr/bin:/bin HOME=$OUT/home XDG_CONFIG_HOME=$OUT/home/.config XDG_CACHE_HOME=$OUT/home/.cache TMPDIR=$OUT/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 180 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$OUT/profile --hide-scrollbars --window-size=1000,${H:-16000} --screenshot=$OUT/page.png "file://$PAGE" >/dev/null 2>&1` | Takes the screenshot. `env -i` starts the browser with an empty environment and sets only six variables: a short `PATH`, the home folder and the two `XDG` folders for settings and for cached files, all inside the output folder, `TMPDIR` as the folder for temporary files, and `FONTCONFIG_FILE` as the font settings file in the folder `A`. So the browser reads no settings of the user. `timeout 180` ends the browser when it still runs after 180 s. `--headless` runs it without a window. `--no-sandbox` and `--disable-gpu` switch off the sandbox and the graphics hardware, and `--disable-dev-shm-usage` keeps the browser from the shared memory folder `/dev/shm`. The seven options from `--no-first-run` to `--disable-breakpad` switch off the first-run steps, background network services, component updates, account sync, extensions and crash reports. `--host-resolver-rules="MAP * ~NOTFOUND"` makes every host name unknown, so the page can load nothing from the network. `--user-data-dir` names the profile folder. `--hide-scrollbars` and `--window-size` give a window of 1000 px width without scroll bars. Its height is the value of the variable `H`, or 16000 px when `H` is not set or empty (`${H:-16000}`). `--screenshot` writes the picture of the window to `page.png` in the output folder. The last argument is the page as a `file://` address. `>/dev/null 2>&1` discards the standard output of the browser and its error messages. |
| 10 | `python3 - <<P` | Starts `python3` and gives it the next lines as its program, up to the line that holds only `P`. The `-` tells `python3` to read the program from its standard input, and `<<P` feeds these lines to it. The end mark `P` has no quotes, so the shell first replaces `$OUT` in the lines by the path of the output folder. |
| 11 | `from PIL import Image` | Python: imports the class `Image` of the picture library Pillow. |
| 12 | `import numpy as np` | Python: imports the number array library NumPy under the short name `np`. |
| 13 | `Image.MAX_IMAGE_PIXELS=None` | Python: switches off the size check of Pillow. With the check, Pillow warns about a picture of more than 89478485 pixels and refuses one of more than twice that number. A screenshot of 1000 px by 16000 px has 16 million pixels, so the check matters only for a much taller window. |
| 14 | `im=Image.open('$OUT/page.png').convert('RGB'); a=np.asarray(im)` | Python: opens the screenshot and turns it into a picture with a red, a green and a blue value per pixel. `a` holds these values as an array with one entry per pixel row, pixel column and color. |
| 15 | `rows=np.where((a<250).any(axis=(1,2)))[0]; h=min(int(rows.max())+20, im.size[1]); k=0` | Python: three statements. `rows` holds the numbers of the pixel rows in which at least one color value is below 250, so the rows that are not white or nearly white all over. `h` is the last such row plus 20 px, but at most the height of the picture. This is the height of the content. `k` counts the pieces from 0. A picture without such a row stops Python with an error here. |
| 16 | `for y in range(0,h,1500):` | Python: loop over the upper edges of the pieces: 0, 1500, 3000 and so on, as long as the edge is below `h`. |
| 17 | `    im.crop((0,y,1000,min(y+1500,h))).save('$OUT/page-%02d.png'%k); k+=1` | Python: cuts the piece from row `y` down to row `y + 1500`, or down to `h` for the last piece, over the width of 1000 px. It saves the piece in the output folder as `page-00.png`, `page-01.png` and so on, and counts it. |
| 18 | `print('content height', h, 'of window', im.size[1], 'pieces', k)` | Python: prints the content height, the height of the screenshot and the number of pieces. The screenshot shows only the window. So when the two heights are equal, the page can go on below the screenshot. |
| 19 | `P` | Ends the Python program that began in line 10. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/render.sh`: the older screenshot script, with `timeout 120` and a default window height of 15500 px.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/render/fontconfig/fonts.conf`: the font settings file on the agent server. The code repo holds no copy of it.
- [Ref3] external source: the list of Chrome flags for tools of the project chrome-launcher, for the meaning of the browser options: https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md
- [Ref4] external source: the article "Getting Started with Headless Chrome" of the Chrome developer site, for the option `--screenshot` and the window size: https://developer.chrome.com/blog/headless-chrome
