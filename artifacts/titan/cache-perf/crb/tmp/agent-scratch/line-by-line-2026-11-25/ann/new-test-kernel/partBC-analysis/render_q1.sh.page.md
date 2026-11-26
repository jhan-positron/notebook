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

1. The script stops at the first failed command from here on ({L4}).
2. It turns the two arguments into full paths and creates the output folder ({L5}).
3. It sets the path of the folder that holds the font settings, and the path of the browser ({L6-7}).
4. It deletes the profile folder and the pictures of an earlier call, and creates the folders that the browser needs ({L8}).
5. It runs the browser, which writes the screenshot `page.png` ({L9}).
6. A Python program finds the height of the content, cuts the screenshot into pieces of 1500 px, and prints the heights and the number of pieces ({L10-19}).

## Behavior a reader must know

- The script deletes files: the folder `profile` and every `page*.png` of the output folder ({L8}). An older `page.png` and its pieces are replaced.
- The screenshot shows only the window, 1000 px wide and 16000 px high unless the variable `H` gives another height [Ref4]. A longer page is cut at the lower edge. The printed line gives both heights ({L18}).
- The page is drawn without the network: every host name is unknown to the browser ({L9}). A page that needs a file from another server is drawn without it.
- The fonts come from the font settings file of the folder `A`. That file maps the font names `system-ui` and `monospace` to the fonts DejaVu Sans and DejaVu Sans Mono [Ref2]. So the text of the screenshot can have other widths than in the browser of a reader.
- With `set -e` the Python part does not run when the browser fails or is ended by `timeout` after 180 s. The exit status of the script is then that of the failed command.
- The paths of the browser and of the font settings are fixed to the agent server ({L6-7}). On another machine the script needs other paths.
- The value of `OUT` stands without quotes in the browser command ({L9}). An output path with a space would break that command.
- The comment in {L3} calls the command the same as in `render.sh`. Apart from the paths, two values differ: the time limit and the default window height [Ref1]. The older script keeps the profile folder, the home folder and the folder for temporary files in its own folder `render`. This script keeps them in the output folder.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/render.sh`: the older screenshot script, with `timeout 120` and a default window height of 15500 px.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/render/fontconfig/fonts.conf`: the font settings file on the agent server. The code repo holds no copy of it.
- [Ref3] external source: the list of Chrome flags for tools of the project chrome-launcher, for the meaning of the browser options: https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md
- [Ref4] external source: the article "Getting Started with Headless Chrome" of the Chrome developer site, for the option `--screenshot` and the window size: https://developer.chrome.com/blog/headless-chrome
