"""Render the Arm support email as HTML (file and mail body), plain text and Markdown.

The text lives in one place (BLOCKS) so the three outputs cannot drift apart.
The boot table and the record totals are recomputed from the saved kernel logs
and compared with the typed values; a mismatch stops the script.
"""
import html
import os
import re
import sys

out_dir = sys.argv[1]
results = os.path.expanduser("~/workspace/titan/cache-perf/crb/results")

SUBJECT = ("Phoenix Reference Server (AGI-CPU-CRB, EVT0, firmware 0.7.2) "
           "starts with 10 of 12 DIMMs at 8000 MT/s")

# ---------------------------------------------------------------- typed values
BOOT_ROWS = [
    ["1", "2026-09-29 01:42", "12", "377.0 GiB", "0"],
    ["2", "2026-09-29 02:09", "12", "377.0 GiB", "1 recoverable"],
    ["3", "2026-10-03 15:34", "10", "314.0 GiB", "0 in 35 s of log"],
    ["4", "2026-10-05 15:52", "12", "377.0 GiB", "0"],
    ["5", "2026-10-20 19:06", "12", "377.0 GiB", "0"],
    ["6", "2026-10-22 05:43", "10", "314.0 GiB", "301 corrected"],
    ["7", "2026-11-09 21:20", "12", "377.0 GiB", "321 corrected"],
    ["8", "2026-11-17 03:48", "10", "314.0 GiB", "4 corrected"],
    ["9", "2026-11-17 03:57", "10", "314.0 GiB", "5 corrected"],
    ["10", "2026-11-17 04:09", "12", "377.0 GiB", "0"],
    ["11", "2026-11-17 04:17", "10", "314.0 GiB", "21 corrected"],
    ["12", "2026-11-17 05:45", "12", "377.0 GiB", "1 recoverable"],
]
TOTAL_RECORDS, WITH_SECTION, CORRECTED, RECOVERABLE = 654, 640, 652, 2
SOURCE_NAMES = ["DDS0_CP1", "DDS1_CP0", "DDS1_CP1", "DDS2_CP0", "DDS3_CP0",
                "DDS4_CP0", "DDS5_CP0", "DDS5_CP1", "DDS6_CP1", "DDS7_CP1"]

# ------------------------------------------------- recompute from the raw logs
MONTH = {"Sep": "09", "Oct": "10", "Nov": "11"}
computed, names, tot, sect, corr, reco = [], set(), 0, 0, 0, 0
for n, rel in enumerate(range(-11, 1), start=1):
    text = open(f"{results}/dimm-check-20261117/k{rel}.txt", errors="replace").read()
    mon, day, hhmm = re.match(r"(\w{3}) (\d{2}) (\d{2}:\d{2}):\d{2} ", text).groups()
    count = re.search(r"This system has (\d+) DIMM sockets", text).group(1)
    avail_k = int(re.search(r"Memory: (\d+)K/\d+K available", text).group(1))
    sev = re.findall(r"event severity: (\w+)", text)
    c, r = sev.count("corrected"), sev.count("recoverable")
    assert c + r == len(sev), sev
    rec = f"{c} corrected" if c else (f"{r} recoverable" if r else "0")
    if n == 3:
        rec = "0 in 35 s of log"
    computed.append([str(n), f"2026-{MONTH[mon]}-{day} {hhmm}", count,
                     f"{avail_k / 2**20:.1f} GiB", rec])
    tot += len(sev); corr += c; reco += r
    sect += len(re.findall(r"section type: unknown, bf32d4d5-b427-4025-8495-8a9e5d4030e4", text))
    assert len(re.findall(r"section type:", text)) == len(
        re.findall(r"section type: unknown, bf32d4d5", text))
    names |= set(re.findall(r"DDS\d_CP\d", text))
assert computed == BOOT_ROWS, computed
assert (tot, sect, corr, reco) == (TOTAL_RECORDS, WITH_SECTION, CORRECTED, RECOVERABLE), (tot, sect, corr, reco)
assert sorted(names) == SOURCE_NAMES, sorted(names)
assert sum(r[2] == "12" for r in BOOT_ROWS) == 7 and sum(r[2] == "10" for r in BOOT_ROWS) == 5
assert abs((7 / 12) ** 6 - 0.039) < 0.0005
assert round((362.15 - 468.05) / 468.05 * 100) == -23

# ----------------------------------------------------------------------- text
# Inline markup in the strings: `code` and **bold**.
BLOCKS = [
    ("p", "Hello Arm Support team,"),

    ("h", "Short version"),
    ("p", "Our Phoenix Reference Server started with only 10 of its 12 memory modules in "
          "5 of 12 boots at the memory speed 8000 MT/s. After we set the speed to 7200 MT/s, "
          "6 of 6 reboots gave 12 modules. Please confirm whether this is the known issue "
          "\"Intermittent DCS delay training failures\" [Ref1], and please answer the five "
          "questions in section 6."),

    ("glossary", "Words used here", [
        ("Module, DIMM", "one memory module. The server has 12 slots, 6 per half of the chip."),
        ("CP0, CP1", "the two halves of the chip in the slot names. `DIMM_CP0_5` is slot 5 of half 0."),
        ("DDR5", "the memory standard of the modules."),
        ("MT/s", "million transfers per second, the unit of memory speed."),
        ("GiB", "2^30 bytes."),
        ("EVT0, EVT1", "revisions of the circuit board. EVT1 is the later one."),
        ("SMBIOS", "the table in which the firmware lists the hardware for the operating system. "
                   "The command `dmidecode` prints it."),
        ("Training", "the step at power-on where the firmware tunes the signal timing of each "
                     "memory module. DCS is a control signal of a DDR5 module. "
                     "\"DCS delay training\" is one training step."),
        ("Error record", "a message that the firmware passes to Linux when hardware reports an "
                         "error. Linux prints it in the kernel log with the tag `[Hardware Error]`."),
        ("BMC", "the management controller on the board."),
        ("SCP", "the system control processor. It runs the first firmware stage."),
        ("Warm reboot", "a restart from Linux without a power-off."),
        ("UTC", "Coordinated Universal Time. All times in this email are UTC."),
        ("est.", "estimated, not measured directly."),
    ]),

    ("h", "1. System"),
    ("table", ["Item", "Value"], [
        ["Product", "Phoenix Reference Server, product family AGI-CPU-CRB, 128 cores"],
        ["Board version", "EVT0"],
        ["Motherboard", "Quanta Computer Inc., version A1DI0, serial number T31S9AMB0050622000T"],
        ["Firmware", "`AGI-CPU-CRB-v0.7.2`, date field 09/08/2026"],
        ["Linux kernel", "`7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858`, the same in all boots"],
        ["Memory modules", "12 x 32 GiB DDR5 registered modules, Micron, part "
                           "`MTC20F2085S1RC80BH1 NCKK`. All 12 slots hold a module."],
        ["Setting \"DIMM Frequency\"", "8000 MT/s until 2026-11-17 19:43, 7200 MT/s since then"],
        ["Settings \"DIMM 0 Enable\" to \"DIMM 5 Enable\"", "all 1 (enabled)"],
        ["Settings \"DIMM PMIC VDD (mV)\" and \"DIMM PMIC VDDQ (mV)\" (the supply voltages "
         "of the modules)", "1100 mV each"],
        ["BMC firmware version", "not collected yet"],
    ], None),
    ("ul", [
        "The firmware version, its date and the board version come from the identity output "
        "of `uefisettings` [Ref7]. This is the settings tool from your Arm AGI CPU Welcome Kit.",
        "The motherboard data and the module data come from the SMBIOS table [Ref6].",
        "The settings come from the settings list of the same tool [Ref7].",
    ]),

    ("h", "2. Symptom"),
    ("ul", [
        "Some boots show all 12 modules. The kernel then reports 377.0 GiB of usable memory.",
        "Other boots show 10 modules. The kernel then reports 314.0 GiB.",
        "No saved boot shows 11 modules.",
        "The firmware removes the two modules before Linux starts. In a 10-module boot the "
        "SMBIOS table has 10 module entries [Ref6]. The memory total in the kernel log is then "
        "exactly 64 GiB smaller (two modules of 32 GiB) [Ref5].",
        "Two 10-module boots were checked for the slot names. Both miss slot 5 on each half.",
    ]),
    ("table", ["Slot", "Serial number", "In the 12-module listing", "In the 10-module listing"], [
        ["`DIMM_CP0_5`", "00-2c-0f-26-09-568a26d4", "yes", "no"],
        ["`DIMM_CP1_5`", "00-2c-0f-26-09-568a449a", "yes", "no"],
    ], None),
    ("ul", [
        "The first 10-module listing was saved on 2026-10-30 [Ref6]. The second one was read "
        "on the screen on 2026-11-17 and was not saved.",
        "The other 10 slots carry the same serial numbers in the saved 10-module listing and "
        "in the 12-module listing [Ref6].",
        "The other three 10-module boots have no module listing.",
        "Linux does not explain the difference. The kernel version is the same in all boots, "
        "and the kernel command line has no memory limit option [Ref5].",
        "Effect on our work: a memory read test with 120 threads reached 362.2 GB/s with "
        "10 modules and 468.1 GB/s with 12 modules. That is 23 % lower. The 1-minute load "
        "average at the start of the two runs was 0.26 and 0.00.",
    ]),

    ("h", "3. Boot history at 8000 MT/s"),
    ("p", "The table lists all 12 boots that the Linux log store of the server held on "
          "2026-11-17 at 06:30 [Ref5]."),
    ("table", ["Boot", "Linux start (UTC)", "Modules", "Usable memory", "Error records"],
     BOOT_ROWS, 2),
    ("ul", [
        "Totals: 7 boots with 12 modules, 5 boots with 10 modules.",
        "The module count comes from the kernel line "
        "`ghes_edac: This system has N DIMM sockets` [Ref5].",
        "The saved log of boot 3 covers only 35 s and ends at a jump of the system clock. "
        "Its start time and its record count are not reliable.",
        "Boots 8 to 11 were reboots for a test of the TXREQ firmware settings. These settings "
        "limit the read requests of the cores, and they are not memory settings.",
        "The module count did not follow the TXREQ settings. Boot 11 ran with the original "
        "settings and showed 10 modules. Boots 7 and 12 ran with the original settings and "
        "showed 12 modules.",
        "The gap between the last log line of one boot and the first kernel line of the next "
        "boot is our estimate of the Linux shutdown time plus the firmware start time.",
        "A direct reboot is a restart with no pause between the two boots. The gap was 231 to "
        "260 s (est.) for the four direct reboots that gave 10 modules. It was 203 s and "
        "224 s (est.) for the two direct reboots that gave 12 modules.",
    ]),

    ("h", "4. Test at 7200 MT/s"),
    ("ul", [
        "Your changelog recommends 7200 MT/s for firmware 0.7.2 [Ref2].",
        "On 2026-11-17 at 19:43 we changed \"DIMM Frequency\" from 8000 MT/s to 7200 MT/s "
        "with `uefisettings`. The tool confirmed the change [Ref8].",
        "We then did 6 warm reboots in a row. We fixed the number 6 before the first reboot.",
        "All 6 boots showed 12 modules, each at 7200 MT/s in the SMBIOS table [Ref8].",
        "The first 5 of these boots ran Linux for only 10 to 17 s each.",
        "5 of the 6 boots logged 0 error records. One boot logged 1 recoverable record with "
        "the source name DDS1_CP1 in its first second.",
        "At 8000 MT/s, 5 of 12 boots showed 10 modules. If that rate still applied, 6 boots "
        "with 12 modules in a row would occur with a probability of 3.9 % (est., from (7/12)^6).",
        "So the result supports the memory speed as the cause. It does not prove it.",
        "The gap before each of these 6 boots was 170 to 182 s (est.).",
        "A start after a power-off was not tested at 7200 MT/s.",
        "The setting is still 7200 MT/s.",
    ]),

    ("h", "5. Error records in the kernel log"),
    ("ul", [
        "The kernel logs of the 12 boots at 8000 MT/s hold 654 firmware error records [Ref5].",
        "652 records have the severity \"corrected\", and 2 records have the severity "
        "\"recoverable\".",
        "640 records carry a data section. The section type is always "
        "`bf32d4d5-b427-4025-8495-8a9e5d4030e4`.",
        "Linux prints `section type: unknown` for this type. Linux therefore does not decode "
        "the records.",
        "Each data section contains a source name. The names seen are DDS0_CP1, DDS1_CP0, "
        "DDS1_CP1, DDS2_CP0, DDS3_CP0, DDS4_CP0, DDS5_CP0, DDS5_CP1, DDS6_CP1 and DDS7_CP1.",
        "Records appear with 10 modules and with 12 modules. Boot 6 (10 modules) logged "
        "301 corrected records. Boot 7 (12 modules) logged 321 corrected records.",
        "The most frequent source names differ between these two boots. In boot 6 they are "
        "DDS5_CP1 (112 records) and DDS1_CP0 (98 records). In boot 7 they are DDS3_CP0 "
        "(123 records) and DDS7_CP1 (119 records).",
        "Boots 2 and 12 each logged 1 recoverable record with the source name DDS1_CP1 in "
        "the first second of the boot. One boot at 7200 MT/s did the same (section 4).",
        "In boots 8, 9 and 11 the first record came 0 to 41 s after the start of a memory "
        "test with 120 threads. Boot 10 ran the same test for about 3.5 minutes and logged "
        "0 records.",
        "No kernel message reports a DIMM error or a training error.",
        "Hypothesis: the records are corrected errors of the memory links, and memory "
        "traffic triggers them. Your decoding of the records would confirm or reject it.",
    ]),

    ("h", "6. Questions"),
    ("ol", [
        "Is the 10-of-12 module result on firmware 0.7.2 at 8000 MT/s the known issue "
        "\"Intermittent DCS delay training failures\"? Your user guide for firmware 0.9.0 "
        "states: \"When a training failure occurs, the affected DIMM is isolated, and boot "
        "continues with fewer DIMMs.\" [Ref1] The text names no memory speed and no earlier "
        "firmware version.",
        "Is the part `MTC20F2085S1RC80BH1 NCKK` validated on an EVT0 board, and at which "
        "speed? The validated lists of the user guide name `MTC20F2085S1RC80BH1 P8CH` and "
        "`MTC20F2085S1RC80BHY M8CC` [Ref3]. They do not name the NCKK part. A test report in "
        "your kit shows the NCKK part at 8000 MT/s on an EVT1 board with firmware 0.9.0 [Ref10].",
        "What do the error records with the section type "
        "`bf32d4d5-b427-4025-8495-8a9e5d4030e4` and the source names DDS0 to DDS7 mean?",
        "Which log shows the training result per slot, and how do we collect it?",
        "Does our EVT0 board need a hardware change to run at 8000 MT/s? The user guide "
        "states: \"DDR 8000 MT/s validation used EVT1 PCBs. Previous PCB versions might "
        "produce a higher error rate.\" [Ref4]",
    ]),

    ("h", "7. Logs and steps to reproduce"),
    ("ul", [
        "Your Quick Start Guide asks for BMC logs and SCP logs with a support case [Ref9]. "
        "These logs are not attached, and we have not collected them yet.",
        "Please tell us which logs you need and how to collect them.",
        "The server now runs at 7200 MT/s. Please tell us if you need a capture from a new "
        "10-module boot at 8000 MT/s.",
    ]),
    ("p", "Steps to reproduce at 8000 MT/s:"),
    ("ol", [
        "Set the speed with `uefisettings`: "
        "`sudo ./uefisettings hii set \"DIMM Frequency\" \"8000 MT/s\"`",
        "Reboot: `sudo systemctl reboot`",
        "After the boot, read the module count: `sudo dmesg | grep \"DIMM sockets\"`",
        "Read the module list: `sudo dmidecode -t 17`",
        "Repeat steps 2 to 4. In our history 5 of 12 boots showed 10 modules.",
    ]),

    ("h", "Attachment"),
    ("p", "One file: `crb-dimm-evidence-20261117.zip` (26 files). Its folders:"),
    ("ul", [
        "`kernel-logs-8000MTs`: the kernel logs of the 12 boots of section 3. Each file name "
        "carries the boot number, the start time and the module count.",
        "`module-lists`: the `dmidecode` outputs with 10 modules (2026-10-30), with 12 modules "
        "at 8000 MT/s and with 12 modules at 7200 MT/s, and the motherboard data.",
        "`firmware`: the firmware identity and the full settings list at 8000 MT/s.",
        "`test-7200MTs`: the reply of the settings tool, and the check output after each of "
        "the 6 reboots.",
    ]),

    ("h", "References"),
    ("refs", [
        "[Ref1] Arm AGI CPU CRB System Validation Kit User Guide, Revision 3.0, section 2.3 "
        "\"Known Issues\", page 9.",
        "[Ref2] Arm AGI CPU Welcome Kit, file `CHANGELOG.md`, section \"Welcome Kit v0.7\", "
        "note \"IMPORTANT — DIMM tuning for firmware 0.7.2\".",
        "[Ref3] The same user guide, section 2.7 \"Memory and Expansion Modules\", "
        "pages 12 and 13.",
        "[Ref4] The same user guide, section 2.8 \"Known Limitations\", page 14.",
        "[Ref5] Attachment, folder `kernel-logs-8000MTs`.",
        "[Ref6] Attachment, folder `module-lists`.",
        "[Ref7] Attachment, folder `firmware`.",
        "[Ref8] Attachment, folder `test-7200MTs`.",
        "[Ref9] Arm AGI CPU 1OU Reference Server Quick Start Guide, document 112283_a0_01_en, "
        "part \"Validate and Deploy\", step 3 \"Provide the following data to Arm Support\".",
        "[Ref10] Arm AGI CPU Welcome Kit, file "
        "`tools/asct/reports/asct_run_output_a1_numa2_ddr_8000.txt`, lines 41 to 54.",
    ]),

    ("p", "Regards,"),
]

# ------------------------------------------------------------------ renderers
FONT = "font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.45;color:#1f2328;"
CODE = ("font-family:Consolas,'Courier New',monospace;font-size:13px;"
        "background:#f1f3f5;padding:1px 3px;border-radius:3px;")
TD = "border:1px solid #c8ccd1;padding:4px 9px;text-align:left;vertical-align:top;"
TH = TD + "background:#eef1f4;font-weight:bold;"
H = "font-size:16px;margin:22px 0 6px 0;color:#1f2328;"


def inline_html(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: f'<code style="{CODE}">{m.group(1)}</code>', s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


def inline_text(s):
    def code(m):
        c = m.group(1)
        quote = " " in c and '"' not in c and not c.startswith("sudo ")  # commands stay bare
        return f'"{c}"' if quote else c
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", re.sub(r"`([^`]+)`", code, s))


def render_html(fold_glossary):
    o = []
    for b in BLOCKS:
        kind = b[0]
        if kind == "h":
            o.append(f'<h2 style="{H}">{inline_html(b[1])}</h2>')
        elif kind == "p":
            o.append(f'<p style="margin:8px 0;">{inline_html(b[1])}</p>')
        elif kind in ("ul", "ol"):
            items = "".join(f'<li style="margin:3px 0;">{inline_html(i)}</li>' for i in b[1])
            o.append(f'<{kind} style="margin:6px 0 10px 0;padding-left:24px;">{items}</{kind}>')
        elif kind == "refs":
            items = "".join(f'<li style="margin:3px 0;">{inline_html(i)}</li>' for i in b[1])
            o.append(f'<ul style="margin:6px 0 10px 0;padding-left:0;list-style:none;">{items}</ul>')
        elif kind == "glossary":
            items = "".join(
                f'<li style="margin:3px 0;"><b>{inline_html(t)}</b>: {inline_html(d)}</li>'
                for t, d in b[2])
            lst = f'<ul style="margin:6px 0 10px 0;padding-left:24px;">{items}</ul>'
            if fold_glossary:
                o.append(f'<details style="margin:14px 0;"><summary style="cursor:pointer;'
                         f'font-weight:bold;font-size:16px;">{b[1]}</summary>{lst}</details>')
            else:
                o.append(f'<h2 style="{H}">{b[1]}</h2>{lst}')
        elif kind == "table":
            _, head, rows, mark_col = b
            th = "".join(f'<th style="{TH}">{inline_html(c)}</th>' for c in head)
            trs = []
            for r in rows:
                low = mark_col is not None and r[mark_col] == "10"
                bg = "background:#fdecd2;" if low else ""
                tds = "".join(
                    f'<td style="{TD}{bg}">'
                    + (f"<b>{inline_html(c)}</b>" if low and i == mark_col else inline_html(c))
                    + "</td>" for i, c in enumerate(r))
                trs.append(f"<tr>{tds}</tr>")
            o.append(f'<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
                     f'margin:8px 0 10px 0;{FONT}"><tr>{th}</tr>{"".join(trs)}</table>')
    return f'<div style="{FONT}max-width:860px;">' + "\n".join(o) + "</div>"


def render_text():
    o = []
    for b in BLOCKS:
        kind = b[0]
        if kind == "h":
            o += ["", inline_text(b[1]).upper(), ""]
        elif kind == "p":
            o += [inline_text(b[1]), ""]
        elif kind == "ul":
            o += [f"- {inline_text(i)}" for i in b[1]] + [""]
        elif kind == "ol":
            o += [f"{n}. {inline_text(i)}" for n, i in enumerate(b[1], 1)] + [""]
        elif kind == "refs":
            o += [inline_text(i) for i in b[1]] + [""]
        elif kind == "glossary":
            o += ["", b[1].upper(), ""] + [f"- {t}: {inline_text(d)}" for t, d in b[2]] + [""]
        elif kind == "table":
            _, head, rows, _mark = b
            cells = [[inline_text(c) for c in r] for r in [head] + rows]
            if len(head) == 2:  # two wide columns: one "item: value" line per row
                o += [f"- {r[0]}: {r[1]}" for r in cells[1:]] + [""]
            else:
                w = [max(len(r[i]) for r in cells) for i in range(len(head))]
                o += ["  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip() for r in cells] + [""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(o)).strip() + "\n"


def render_md():
    o = []
    for b in BLOCKS:
        kind = b[0]
        if kind == "h":
            o += [f"### {b[1]}", ""]
        elif kind == "p":
            o += [b[1], ""]
        elif kind == "ul":
            o += [f"- {i}" for i in b[1]] + [""]
        elif kind == "ol":
            o += [f"{n}. {i}" for n, i in enumerate(b[1], 1)] + [""]
        elif kind == "refs":
            o += [f"- {i}" for i in b[1]] + [""]
        elif kind == "glossary":
            o += [f"### {b[1]}", ""] + [f"- **{t}**: {d}" for t, d in b[2]] + [""]
        elif kind == "table":
            _, head, rows, mark_col = b
            o.append("| " + " | ".join(head) + " |")
            o.append("|" + "---|" * len(head))
            for r in rows:
                low = mark_col is not None and r[mark_col] == "10"
                cells = [f"**{c}**" if low and i == mark_col else c.replace("|", "\\|")
                         for i, c in enumerate(r)]
                o.append("| " + " | ".join(cells) + " |")
            o.append("")
    return "\n".join(o).strip() + "\n"


def render_lean():
    esc = lambda t: re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>",
                           re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(t, quote=False)))
    o = []
    for b in BLOCKS:
        kind = b[0]
        if kind == "h":
            o.append(f"<h3>{esc(b[1])}</h3>")
        elif kind == "p":
            o.append(f"<p>{esc(b[1])}</p>")
        elif kind in ("ul", "ol"):
            o.append(f"<{kind}>" + "".join(f"<li>{esc(i)}</li>" for i in b[1]) + f"</{kind}>")
        elif kind == "refs":
            o.append("<p>" + "<br>".join(esc(i) for i in b[1]) + "</p>")
        elif kind == "glossary":
            o.append(f"<h3>{b[1]}</h3><ul>"
                     + "".join(f"<li><b>{esc(t)}</b>: {esc(d)}</li>" for t, d in b[2]) + "</ul>")
        elif kind == "table":
            _, head, rows, mark_col = b
            trs = ["<tr>" + "".join(f'<th align="left" bgcolor="#eef1f4">{esc(c)}</th>' for c in head) + "</tr>"]
            for r in rows:
                low = mark_col is not None and r[mark_col] == "10"
                tds = "".join("<td>" + (f"<b>{esc(c)}</b>" if low and i == mark_col else esc(c)) + "</td>"
                              for i, c in enumerate(r))
                trs.append(('<tr bgcolor="#fdecd2">' if low else "<tr>") + tds + "</tr>")
            o.append('<table border="1" cellpadding="5" cellspacing="0" '
                     'style="border-collapse:collapse;border-color:#c8ccd1">' + "".join(trs) + "</table>")
    return ('<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2328">'
            + "\n".join(o) + "</div>")


os.makedirs(out_dir, exist_ok=True)
body = render_lean()
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email draft to Arm Support</title>
</head>
<body style="background:#ffffff;margin:0;padding:24px 16px;">
<div style="{FONT}max-width:860px;margin:0 auto;">
<p style="margin:0 0 4px 0;"><b>To:</b> support@arm.com</p>
<p style="margin:0 0 4px 0;"><b>Subject:</b> {html.escape(SUBJECT)}</p>
<p style="margin:0 0 14px 0;"><b>Attachment:</b> crb-dimm-evidence-20261117.zip</p>
<hr style="border:0;border-top:1px solid #c8ccd1;margin:0 0 14px 0;">
</div>
<div style="max-width:860px;margin:0 auto;">
{render_html(fold_glossary=True)}
</div>
</body>
</html>
"""
files = {
    "email-to-arm-support.html": page,
    "email-to-arm-support.txt": f"To: support@arm.com\nSubject: {SUBJECT}\n\n" + render_text(),
    "email-body-for-gmail.html": body,
    "email-to-arm-support.md": render_md(),
}
for name, text in files.items():
    dest = out_dir if name.endswith(("support.html", "support.txt")) else sys.argv[2]
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, name), "w") as f:
        f.write(text)
    print(f"{len(text):>7} chars  {os.path.join(dest, name)}")
print("subject:", SUBJECT)
print("checks passed: boot table, record totals, source names, 3.9 %, -23 %")
