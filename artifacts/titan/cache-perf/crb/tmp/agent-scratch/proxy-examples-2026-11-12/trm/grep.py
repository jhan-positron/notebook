# Count pages matching a regex, print page numbers (1-based PDF index) and hit counts.
import re, sys, glob, os
pat = re.compile(sys.argv[2], re.I if len(sys.argv) < 4 else 0)
for f in sorted(glob.glob(os.path.join(sys.argv[1], "p*.txt"))):
    t = open(f).read()
    n = len(pat.findall(t))
    if n: print(os.path.basename(f)[1:5], n, end="; ")
print()
