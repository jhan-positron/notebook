import re,sys
def load(f):
    L={}
    for l in open(f).read().split('\n'):
        m=re.match(r'(\d+): (.*)',l)
        if m: L[int(m.group(1))]=m.group(2)
    return L
if __name__=='__main__':
    L=load(sys.argv[1]); a,b=int(sys.argv[2]),int(sys.argv[3]); skip=set(map(int,sys.argv[4:]))
    for n in range(a,b+1):
        if n in L and n not in skip: print(n,L[n][:7000]); print()
