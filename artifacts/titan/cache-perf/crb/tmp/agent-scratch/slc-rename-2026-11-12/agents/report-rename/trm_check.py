import sys
sys.path.append(sys.argv[1])
import fitz, re
p = sys.argv[2]
d = fitz.open(p)
print("pages", d.page_count)
for i in range(25, 36):
    t = d[i].get_text()
    for m in re.finditer(r'Table 1-9[^\n]*|[^\n]*\b[Ww]ays\b[^\n]*', t):
        print(i, repr(d[i].get_label()), '|', m.group(0).strip())
for i in range(48, 60):
    t = d[i].get_text().replace('\n', ' ')
    for m in re.finditer(r'The System Level Cache \(SLC\) is a last-level cache[^.]*\.', t):
        print("QUOTE at pdf index", i, "label", repr(d[i].get_label()), ":", m.group(0)[:200])
for i in range(12, 24):
    t = d[i].get_text().replace('\n', ' ')
    for m in re.finditer(r'[Ee]ach HN-S can contain an SF and an SLC[^.]*\.|Each byte of address space is assigned to a single Home Node[^.]*\.', t):
        print("QUOTE at pdf index", i, "label", repr(d[i].get_label()), ":", m.group(0)[:200])
# printed page number in footer
for i in (18, 30, 53, 54):
    t = d[i].get_text()
    print("index", i, "tail:", repr(t[-120:]))
