const fs = require("fs");
const childProcess = require("child_process");
const chromePath = "/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell";
const profile = fs.mkdtempSync("/tmp/pr5047-browser-");
const chrome = childProcess.spawn(chromePath, [
  "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
  "--no-first-run", "--no-default-browser-check",
  "--remote-debugging-pipe", `--user-data-dir=${profile}`
], {stdio: ["ignore", "ignore", "pipe", "pipe", "pipe"]});
let nextId = 0;
let buffer = "";
let stderr = "";
const pending = new Map();
const runtimeErrors = [];
chrome.stderr.on("data", data => { stderr += data; });
chrome.stdio[3].on("error", () => {});
chrome.stdio[4].on("error", () => {});
chrome.stdio[4].on("data", data => {
  buffer += data;
  let delimiter;
  while ((delimiter = buffer.indexOf("\0")) !== -1) {
    const message = JSON.parse(buffer.slice(0, delimiter));
    buffer = buffer.slice(delimiter + 1);
    if (message.method === "Runtime.exceptionThrown") runtimeErrors.push(message.params);
    if (message.id && pending.has(message.id)) {
      const {resolve, reject, timer} = pending.get(message.id);
      clearTimeout(timer);
      pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    }
  }
});
function call(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => reject(new Error(`Timed out: ${method}\n${stderr}`)), 15000);
    pending.set(id, {resolve, reject, timer});
    chrome.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + "\0");
  });
}
let session;
async function evaluate(expression) {
  const result = await call("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true}, session);
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
async function screenshot(name) {
  await evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))");
  const result = await call("Page.captureScreenshot", {format: "png"}, session);
  fs.writeFileSync(`/tmp/2026-10-20-pr5047-update/${name}.png`, Buffer.from(result.data, "base64"));
}
async function jump(id) {
  await evaluate(`document.getElementById(${JSON.stringify(id)}).scrollIntoView({behavior:"instant",block:"start"})`);
}
(async () => {
  try {
    const target = await call("Target.createTarget", {url: "about:blank"});
    session = (await call("Target.attachToTarget", {targetId: target.targetId, flatten: true})).sessionId;
    await call("Runtime.enable", {}, session);
    await call("Page.enable", {}, session);
    await call("Emulation.setDeviceMetricsOverride", {width: 1360, height: 1100, deviceScaleFactor: 1, mobile: false}, session);
    await call("Page.navigate", {url: "file:///home/jhan/workspace/intel-AMX/random/2026-10-20-pr-5047-line-by-line.html"}, session);
    await evaluate('document.readyState === "complete" ? true : new Promise(resolve => window.addEventListener("load", () => resolve(true), {once:true}))');
    assert(await evaluate('document.querySelectorAll("#new-lines .line.added").length === 25 && document.querySelectorAll("#removed-lines .line.removed").length === 43'), "Line coverage in rendered document");
    assert(await evaluate('document.querySelectorAll(".line.context").length === 35'), "Context coverage");
    const width = await evaluate("({viewport:innerWidth,body:document.documentElement.scrollWidth})");
    assert(width.body <= width.viewport, "Desktop page overflows");
    await screenshot("desktop-overview");
    assert(await evaluate('document.querySelectorAll(".second-line.added").length === 235 && document.querySelectorAll(".second-line.removed").length === 284'), "Second commit line coverage");
    assert(await evaluate('document.querySelectorAll(".second-file").length === 9'), "Nine files");
    assert(await evaluate('document.getElementById("perf-chart").textContent.includes("7.18")'), "Benchmark figure present");
    const files = await evaluate(`(() => {
      document.getElementById("expand-second").click();
      const expanded = document.querySelectorAll(".second-file[open]").length;
      document.getElementById("collapse-second").click();
      const collapsed = document.querySelectorAll(".second-file[open]").length;
      document.querySelector('.file-index a').click();
      const linked = document.querySelector('#second-file-1 details').open;
      document.getElementById("collapse-second").click();
      return {expanded,collapsed,linked};
    })()`);
    assert(files.expanded===9 && files.collapsed===0 && files.linked, "File disclosure controls");
    await jump("gptoss");
    await screenshot("desktop-performance");
    await evaluate('document.getElementById("perf-chart").scrollIntoView({behavior:"instant",block:"start"})');
    await screenshot("desktop-chart");
    await evaluate('document.querySelector("#second-file-1 details").open=true');
    await jump("c2-f1-new-1973");
    await screenshot("desktop-new-annotations");
    const mask = await evaluate(`(() => {
      document.getElementById("example").click();
      const initial = document.getElementById("live-value").textContent;
      const states = [];
      for (let i = 0; i < 3; i++) {
        document.getElementById("step").click();
        states.push(document.getElementById("remaining-value").textContent);
      }
      return {initial, states, live:document.getElementById("live-value").textContent,
        scores:[...document.querySelectorAll("#scores tr")].map(row => [...row.querySelectorAll("td")].map(cell => cell.textContent)),
        disabled:document.getElementById("step").disabled};
    })()`);
    assert(mask.initial === mask.live, "Selection mask changed while iterating");
    assert(mask.states.map(state => state.match(/\((\d+)\)/)[1]).join() === "72,64,0", "Iterator states");
    assert(JSON.stringify(mask.scores[0]) === JSON.stringify(["−∞","4","−∞","6","−∞","−∞","9","−∞"]), "First query scores");
    assert(JSON.stringify(mask.scores[1]) === JSON.stringify(["−∞","3","−∞","7","−∞","−∞","13","−∞"]), "Second query scores");
    assert(mask.disabled, "Completed iterator must stop");
    const empty = await evaluate(`(() => {
      document.getElementById("empty").click();
      return document.getElementById("step").disabled &&
        [...document.querySelectorAll("#scores td")].every(cell => cell.textContent === "−∞");
    })()`);
    assert(empty, "Empty selection must preserve initial scores");
    const all = await evaluate(`(() => {
      document.getElementById("all").click();
      for(let i=0;i<8;i++) document.getElementById("step").click();
      return document.getElementById("step").disabled && document.querySelectorAll(".bit.done").length === 8;
    })()`);
    assert(all, "All selected offsets must be scored");
    const toggled = await evaluate(`(() => {
      document.getElementById("empty").click();
      document.querySelector('[data-offset="7"]').click();
      document.getElementById("step").click();
      return document.querySelector(".bit.done").dataset.offset === "7" &&
        document.querySelectorAll("#scores tr")[0].lastElementChild.textContent === "10";
    })()`);
    assert(toggled, "Individual offset toggle");
    const quiz = await evaluate(`(() => {
      return [...document.querySelectorAll(".quiz-item")].map(item => {
        item.querySelector('[data-correct="false"]').click();
        const incorrect = item.querySelector(".feedback").classList.contains("retry");
        item.querySelector('[data-correct="true"]').click();
        return incorrect && item.querySelector(".feedback").classList.contains("good") && !item.querySelector(".feedback").hidden;
      });
    })()`);
    assert(quiz.length === 5 && quiz.every(Boolean), "Quiz feedback");
    const filtered = await evaluate(`(() => {
      const checkbox = document.getElementById("changes-only");
      checkbox.click();
      const hidden = document.querySelectorAll(".hidden-context").length;
      checkbox.click();
      return hidden === 35 && document.querySelectorAll(".hidden-context").length === 0;
    })()`);
    assert(filtered, "Added-line filter");
    await evaluate('document.getElementById("example").click(); document.getElementById("step").click()');
    await jump("intuition");
    await screenshot("desktop-intuition");
    await jump("new-lines");
    await screenshot("desktop-annotations");
    await call("Emulation.setDeviceMetricsOverride", {width: 390, height: 844, deviceScaleFactor: 1, mobile: true}, session);
    await evaluate('window.scrollTo({top:0,behavior:"instant"})');
    const mobile = await evaluate("({viewport:innerWidth,body:document.documentElement.scrollWidth})");
    assert(mobile.body <= mobile.viewport, "Mobile page overflows");
    await screenshot("mobile-overview");
    await jump("gptoss");
    await screenshot("mobile-performance");
    await evaluate('document.getElementById("perf-chart").scrollIntoView({behavior:"instant",block:"start"})');
    await screenshot("mobile-chart");
    await evaluate('document.getElementById("expand-second").click()');
    const expandedWidth = await evaluate("({viewport:innerWidth,body:document.documentElement.scrollWidth})");
    assert(expandedWidth.body <= expandedWidth.viewport, "Expanded mobile page overflows");
    await jump("c2-f1-new-1973");
    await screenshot("mobile-new-annotations");
    await jump("new-lines");
    await screenshot("mobile-annotations");
    assert(runtimeErrors.length === 0, "JavaScript runtime exception");
    console.log(JSON.stringify({desktop: width, mobile, lineCoverage:{added:25,removed:43,context:35},
      maskExample:mask,checks:["empty mask","all offsets","individual toggle","5 quizzes","line filter"],
      secondCommit:{added:235,removed:284,files:9},fileControls:files,runtimeErrors:runtimeErrors.length,screenshots:11}, null, 2));
  } finally {
    const exited = chrome.exitCode !== null ? Promise.resolve() : new Promise(resolve => chrome.once("exit", resolve));
    try { await call("Browser.close"); } catch {}
    if (chrome.exitCode === null) chrome.kill();
    await exited;
    fs.rmSync(profile, {recursive:true, force:true, maxRetries:5, retryDelay:100});
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
