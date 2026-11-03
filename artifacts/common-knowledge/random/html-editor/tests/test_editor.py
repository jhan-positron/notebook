"""Browser checks for the standalone editor. Run with Python and Playwright."""
import os
from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[2]
EDITOR = ROOT / "html-editor.html"
SAMPLE = ROOT / "phoenix-crb-action-plan.html"
FIXTURE = """<!doctype html><!-- keep this comment --><html lang="en"><head>
<meta charset="utf-8"><title>Test document</title>
<style>body{font:16px sans-serif;background:white}td,th{padding:12px;border:1px solid #999} .blue{color:blue}</style>
<script>window.documentScriptRan=true</script></head><body class="original" spellcheck="false">
<h1>Original title</h1><p id="intro">Keep <strong>bold words</strong> and <a href="https://example.com/">this link</a>.</p>
<table id="tasks"><colgroup><col class="blue"><col></colgroup>
<thead><tr><th id="name" scope="col">Name</th><th scope="col">Status</th></tr></thead>
<tbody><tr id="row-a" class="record"><td id="unique" headers="name" class="blue">Alpha</td><td>Ready</td></tr>
<tr><td>Beta</td><td>Pending</td></tr></tbody></table><p>After the table.</p>
<script>window.bodyScriptRan=true</script></body></html>"""


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        options = {"headless": True, "args": ["--no-sandbox"]}
        if os.environ.get("EDITOR_TEST_BROWSER"):
            options["executable_path"] = os.environ["EDITOR_TEST_BROWSER"]
        cls.browser = cls.playwright.chromium.launch(**options)
        print("Browser:", cls.browser.version, flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(6000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(EDITOR.as_uri())
        self.frame = self.page.frame_locator("#document-frame")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def load(self, text=FIXTURE, filename="fixture.html"):
        self.page.locator("#file-input").set_input_files({"name": filename, "mimeType": "text/html", "buffer": text.encode()})
        expect(self.page.locator("#document-frame")).to_be_visible()
        expect(self.page.locator("#filename")).to_have_text(filename)

    def select(self, selector, end=False):
        target = self.frame.locator(selector).first
        target.click()
        target.evaluate("""(element, end) => {
            const selection = element.ownerDocument.getSelection();
            const range = element.ownerDocument.createRange();
            range.selectNodeContents(element);
            if (end) range.collapse(false);
            selection.removeAllRanges(); selection.addRange(range);
            element.ownerDocument.dispatchEvent(new Event('selectionchange'));
        }""", end)
        return target

    def download(self):
        self.page.evaluate("window.showSaveFilePicker = undefined")
        with self.page.expect_download() as event:
            self.page.locator("#save").click()
        return Path(event.value.path()).read_text()

    def install_handles(self, text=FIXTURE):
        # Picker dialogs are replaced; writes, cancellations and errors use the public handle contract.
        self.page.evaluate("""text => {
            window.testFiles = {original:text, copy:''};
            window.testWrites = [];
            const makeHandle = (key, name) => ({name,
                getFile:async () => new File([testFiles[key]],name,{type:'text/html'}),
                isSameEntry:async other => other.name === name,
                createWritable:async () => {
                    if (window.failWrite) throw new Error('Test write failed');
                    let pending;
                    return {write:async text => { pending=text; }, close:async () => {
                        testFiles[key]=pending; testWrites.push(key);
                    }, abort:async () => {}};
                }});
            window.originalHandle=makeHandle('original','fixture.html');
            window.copyHandle=makeHandle('copy','copy.html');
            window.showOpenFilePicker=async () => [originalHandle];
            window.showSaveFilePicker=async () => copyHandle;
        }""", text)
        self.page.locator("#open").click()
        expect(self.page.locator("#filename")).to_have_text("fixture.html")

    def test_sample_round_trip_and_edit(self):
        original = SAMPLE.read_text()
        self.load(original, SAMPLE.name)
        expect(self.frame.locator("table")).to_have_count(5)
        self.assertEqual(self.download(), original)
        styles = self.frame.locator("head style").first.text_content()
        links = self.frame.locator("a").evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))")
        self.select("h1")
        self.page.keyboard.insert_text("Updated action plan — 中文 ✓")
        output = self.download()
        self.assertIn("Updated action plan — 中文 ✓", output)
        self.assertNotIn("data-editor-", output)
        self.assertNotIn('contenteditable="true"', output)
        self.assertNotIn("Content-Security-Policy", output)
        self.assertIn(styles, output)
        self.page.locator("#file-input").set_input_files({"name":"roundtrip.html", "mimeType":"text/html", "buffer":output.encode()})
        expect(self.frame.locator("h1")).to_have_text("Updated action plan — 中文 ✓")
        self.assertEqual(self.frame.locator("a").evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))"), links)
        expect(self.frame.locator("table")).to_have_count(5)

    def test_cell_typing_paste_and_undo(self):
        self.load()
        cell = self.select("#tasks tbody tr:first-child td:nth-child(2)")
        self.page.keyboard.insert_text("Updated")
        expect(cell).to_have_text("Updated")
        self.page.keyboard.press("Control+z")
        expect(cell).to_have_text("Ready")
        self.page.keyboard.press("Control+Shift+z")
        expect(cell).to_have_text("Updated")
        self.select("#tasks tbody tr:first-child td:nth-child(2)")
        cell.evaluate("""element => {
            const clipboardData=new DataTransfer();
            clipboardData.setData('text/plain','Plain <text> & more');
            clipboardData.setData('text/html','<b style="color:red">Unwanted markup</b>');
            element.dispatchEvent(new ClipboardEvent('paste',{clipboardData,bubbles:true,cancelable:true}));
        }""")
        expect(cell).to_have_text("Plain <text> & more")
        expect(cell.locator("b")).to_have_count(0)
        expect(self.page.locator("#save-state")).to_have_text("Unsaved changes")

    def test_rows_columns_history_and_unique_ids(self):
        self.load()
        self.select("#tasks tbody td")
        for button in ["row-above", "row-below"]:
            self.page.locator("#"+button).click()
        expect(self.frame.locator("#tasks tr")).to_have_count(5)
        for button in ["column-left", "column-right"]:
            self.page.locator("#"+button).click()
        self.assertEqual(self.frame.locator("#tasks tr").evaluate_all("rows => rows.map(row => row.cells.length)"), [4]*5)
        expect(self.frame.locator("#unique")).to_have_count(1)
        expect(self.frame.locator("#row-a")).to_have_count(1)
        self.assertEqual(self.frame.locator("#tasks col").evaluate_all("nodes => nodes.reduce((sum,n) => sum+n.span,0)"), 4)
        self.page.locator("#undo").click()
        self.assertEqual(self.frame.locator("#tasks tr").evaluate_all("rows => rows.map(row => row.cells.length)"), [3]*5)
        self.page.locator("#redo").click()
        self.assertEqual(self.frame.locator("#tasks tr").evaluate_all("rows => rows.map(row => row.cells.length)"), [4]*5)

    def test_header_row_inserts_into_body(self):
        self.load()
        self.select("#tasks th")
        self.page.locator("#row-below").click()
        expect(self.frame.locator("#tasks thead tr")).to_have_count(1)
        expect(self.frame.locator("#tasks tbody tr")).to_have_count(3)
        expect(self.frame.locator("#tasks tbody tr:first-child td")).to_have_count(2)
        self.assertEqual(self.frame.locator("#tasks tbody tr:first-child").inner_text().strip(), "")

    def test_merged_and_nested_tables_keep_text_editing(self):
        for table in [
            '<table><tr><td colspan="2">Merged</td></tr><tr><td>A</td><td>B</td></tr></table>',
            '<table><tr><td>Outer<table><tr><td>Nested</td></tr></table></td></tr></table>',
            '<table><tr><td>Short</td></tr><tr><td>A</td><td>B</td></tr></table>',
        ]:
            self.load('<!doctype html><html><body>'+table+'</body></html>')
            cell = self.select("td")
            for button in ["row-above","row-below","column-left","column-right"]:
                expect(self.page.locator("#"+button)).to_be_disabled()
            self.assertTrue(cell.evaluate("element => element.isContentEditable"))

    def test_paragraph_and_table_navigation(self):
        self.load()
        self.select("#tasks tbody td", end=True)
        self.page.keyboard.press("Tab")
        expect(self.page.locator("#table-context")).to_contain_text("Column 2")
        self.page.keyboard.press("Shift+Tab")
        expect(self.page.locator("#table-context")).to_contain_text("Column 1")
        self.page.keyboard.press("Enter")
        self.page.keyboard.insert_text("Second line")
        expect(self.frame.locator("#tasks tr")).to_have_count(3)
        self.page.locator("#paragraph").click()
        self.page.keyboard.insert_text("A new note after the table.")
        expect(self.frame.locator("#tasks + p")).to_have_text("A new note after the table.")
        output = self.download()
        self.assertIn("A new note after the table.", output)

    def test_preview_preserves_edit_and_blocks_typing(self):
        self.load()
        self.select("h1")
        self.page.keyboard.insert_text("Changed title")
        self.page.locator("#preview").click()
        self.assertEqual(self.frame.locator("body").get_attribute("contenteditable"), "false")
        expect(self.page.locator("#paragraph")).to_be_disabled()
        self.frame.locator("h1").click()
        self.page.keyboard.insert_text("Should not appear")
        expect(self.frame.locator("h1")).to_have_text("Changed title")
        self.page.locator("#preview").click()
        expect(self.frame.locator("h1")).to_have_text("Changed title")
        self.page.locator("#undo").click()
        expect(self.frame.locator("h1")).to_have_text("Original title")

    def test_scripts_resources_and_metadata(self):
        requests = []
        self.context.route("https://example.com/**", lambda route: (requests.append(route.request.url), route.abort()))
        source = FIXTURE.replace("</head>", '<meta http-equiv="refresh" content="0;url=https://example.com/redirect"><link rel="stylesheet" href="https://example.com/style.css"></head>')
        source = source.replace("</body>", '<img src="https://example.com/image.png" onerror="parent.hacked=true"><iframe src="https://example.com/frame"></iframe></body>')
        self.load(source)
        self.page.wait_for_timeout(250)
        self.assertEqual(requests, [])
        self.assertFalse(self.page.evaluate("!!window.hacked"))
        self.assertFalse(self.frame.locator("body").evaluate("el => !!el.ownerDocument.defaultView.documentScriptRan || !!el.ownerDocument.defaultView.bodyScriptRan"))
        self.select("h1")
        self.page.keyboard.insert_text("New title")
        output = self.download()
        self.assertIn('window.documentScriptRan=true', output)
        self.assertIn('window.bodyScriptRan=true', output)
        self.assertIn('http-equiv="refresh"', output)
        self.assertIn('class="original" spellcheck="false"', output)
        self.assertIn('<!-- keep this comment -->', output)
        self.assertIn('href="https://example.com/style.css"', output)
        self.assertNotIn('default-src', output)

    def test_native_save_contract_and_save_as(self):
        self.install_handles()
        self.select("h1")
        self.page.keyboard.insert_text("Saved title")
        self.page.keyboard.press("Control+s")
        expect(self.page.locator("#message")).to_have_text("Saved fixture.html.")
        expect(self.page.locator("#save-state")).to_have_text("No unsaved changes")
        saved = self.page.evaluate("testFiles.original")
        self.assertIn("Saved title", saved)
        self.select("h1")
        self.page.keyboard.insert_text("Copied title")
        self.page.locator("#save-as").click()
        expect(self.page.locator("#filename")).to_have_text("copy.html")
        self.assertEqual(self.page.evaluate("testFiles.original"), saved)
        self.assertIn("Copied title", self.page.evaluate("testFiles.copy"))

    def test_write_error_and_external_change_keep_edits(self):
        self.install_handles()
        self.select("h1")
        self.page.keyboard.insert_text("Keep this edit")
        self.page.evaluate("window.failWrite=true")
        self.page.locator("#save").click()
        expect(self.page.locator("#message")).to_contain_text("Test write failed")
        expect(self.page.locator("#save-state")).to_have_text("Unsaved changes")
        self.assertEqual(self.page.evaluate("testFiles.original"), FIXTURE)
        self.page.evaluate("window.failWrite=false; testFiles.original='External edit'")
        self.page.locator("#save").click()
        expect(self.page.locator("#message")).to_contain_text("changed on disk")
        self.assertEqual(self.page.evaluate("testFiles.original"), "External edit")
        expect(self.frame.locator("h1")).to_have_text("Keep this edit")

    def test_cancel_and_discard_confirmation(self):
        self.install_handles()
        self.select("h1")
        self.page.keyboard.insert_text("Unsaved title")
        self.page.evaluate("() => { window.showSaveFilePicker=async()=>{throw new DOMException('Cancelled','AbortError')}; }")
        self.page.locator("#save-as").click()
        expect(self.page.locator("#save-state")).to_have_text("Unsaved changes")
        self.assertEqual(self.page.evaluate("testWrites"), [])
        dialogs = []
        def dismiss(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()
        self.page.on("dialog", dismiss)
        self.page.locator("#open").click()
        self.assertTrue(dialogs)
        expect(self.frame.locator("h1")).to_have_text("Unsaved title")

    def test_cross_cell_deletion_is_blocked(self):
        self.load()
        self.frame.locator("#tasks td").first.click()
        self.frame.locator("#tasks").evaluate("""table => {
            const range=table.ownerDocument.createRange();
            range.setStart(table.rows[1].cells[0].firstChild,0);
            range.setEnd(table.rows[1].cells[1].firstChild,5);
            const selection=table.ownerDocument.getSelection();
            selection.removeAllRanges();selection.addRange(range);
        }""")
        self.page.keyboard.press("Backspace")
        expect(self.frame.locator("#tasks tbody tr:first-child td").first).to_have_text("Alpha")
        expect(self.frame.locator("#tasks tbody tr:first-child td").nth(1)).to_have_text("Ready")
        expect(self.page.locator("#message")).to_contain_text("one table cell")

    def test_narrow_window_and_invalid_file(self):
        self.page.set_viewport_size({"width":720,"height":900})
        self.load()
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.page.locator("#help").click()
        expect(self.page.locator("#help-dialog")).to_be_visible()
        self.page.locator("#close-help").click()
        self.page.locator("#file-input").set_input_files({"name":"wrong.html", "mimeType":"text/html", "buffer":b'\xff\xfeInvalid'})
        expect(self.page.locator("#message")).to_contain_text("not UTF-8")
        expect(self.frame.locator("h1")).to_have_text("Original title")


if __name__ == "__main__":
    unittest.main(verbosity=2)
