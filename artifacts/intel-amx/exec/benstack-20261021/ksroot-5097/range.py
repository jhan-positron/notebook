import sys
f, lo, hi = sys.argv[1], int(sys.argv[2],16), int(sys.argv[3],16)
for line in open(f):
    t = line.split(':',1)
    try: a = int(t[0].strip(),16)
    except: continue
    if lo <= a <= hi: print(line.rstrip())
