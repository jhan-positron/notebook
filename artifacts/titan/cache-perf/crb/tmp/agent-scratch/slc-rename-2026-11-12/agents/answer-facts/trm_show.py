import fitz, sys
p = sys.argv[1]
d = fitz.open(p)
for a in sys.argv[2:]:
    i = int(a)
    print(f'=========== pdf page (1-based) {i} ===========')
    print(d[i-1].get_text())
