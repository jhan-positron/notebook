import pickle, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raw
d = pickle.load(open('raw.pkl', 'rb'))
A, B, D = d['A'], d['B'], d['D']
med = statistics.median
def g(name, kernel, pos=None, rnd=None):
    return [i['total'] for i in D[name] if i['kernel'] == kernel and (pos is None or i['pos'] == pos) and (rnd is None or i['round'] == rnd)]
def rng(v): return '%.2f to %.2f' % (min(v), max(v))
# pools
Lold = sum([g(n, 'oldread', pos=0) for n in ('L-1','L-2a','L-2b','L-3','L-4a','L-4b','L-4c')], [])
Lasm = sum([g(n, 'asmread', pos=1) for n in ('L-1','L-2a','L-2b','L-3','L-4a','L-4b','L-4c')], [])
print('pool L old', len(Lold), rng(Lold), 'med %.4f' % med(Lold), 'width %.4f = %.3f %% of min, %.3f %% of med' % (max(Lold)-min(Lold), (max(Lold)-min(Lold))/min(Lold)*100, (max(Lold)-min(Lold))/med(Lold)*100))
print('pool L asm', len(Lasm), rng(Lasm), 'med %.4f' % med(Lasm), 'width %.4f' % (max(Lasm)-min(Lasm)))
Lasm10 = sorted(Lasm)[1:]
print('pool L asm without lowest', len(Lasm10), rng(Lasm10))
PLold = sum([g(n, 'oldread') for n in ('T72L1','T72L2','T72L3')], [])
PLasm = sum([g(n, 'asmread') for n in ('T72L1','T72L2','T72L3')], [])
print('part L old', len(PLold), rng(PLold), 'med %.4f' % med(PLold))
print('part L asm', len(PLasm), rng(PLasm), 'med %.4f' % med(PLasm))
print(' L old nearest ends %.4f (%.3f %% of pool min) ; medians %.4f (%.3f %% of pool med)' % (min(Lold)-max(PLold), (min(Lold)-max(PLold))/min(Lold)*100, med(Lold)-med(PLold), (med(Lold)-med(PLold))/med(Lold)*100))
print(' L asm nearest ends %.4f ; medians %.4f ; farthest %.5f' % (min(PLasm)-max(Lasm), med(PLasm)-med(Lasm), max(PLasm)-min(Lasm)))
print(' L asm vs pool10 nearest %.4f' % (min(PLasm)-max(Lasm10)))
Fold = g('F72d12','oldread'); Fasm = g('F72d12','asmread')
print('F72d12 old', rng(Fold), 'asm', rng(Fasm), 'med %.4f' % med(Fasm))
print(' part L asm above F72d12: nearest %.4f medians %.4f farthest %.4f' % (min(PLasm)-max(Fasm), med(PLasm)-med(Fasm), max(PLasm)-min(Fasm)))
L1asm = g('L-1','asmread'); L1old = g('L-1','oldread')
print(' F72d12 asm above L-1: %.4f' % (min(Fasm)-max(L1asm)))
Iold = g('T72I1','oldread')+g('T72I2','oldread'); Iasm = g('T72I1','asmread')+g('T72I2','asmread')
print('control I old', rng(Iold), 'asm', rng(Iasm), ' asm above pool %.4f' % (min(Iasm)-max(Lasm)))
Cold = sum([g(n,'oldread') for n in ('T72C1','T72C2','T72C3','T72C4')], [])
print('part C old', len(Cold), rng(Cold))
Cao = g('T72C2','asmread',rnd=1)+g('T72C4','asmread',rnd=1)
print('part C asm after oldread', rng(Cao), 'above pool %.4f' % (min(Cao)-max(Lasm)))
three = Fasm+PLasm+Iasm
print('three visits asm', rng(three), 'span %.4f' % (max(three)-min(three)))
six_old = Fold+PLold+Iold
print('six rows old', rng(six_old), 'span %.4f' % (max(six_old)-min(six_old)))
print('L-1 alone old', rng(L1old), 'asm', rng(L1asm))
# part A
old7200 = [v for k,(vals,h,iv,l) in A.items() if k[2]=='bw_old' for v in vals]
pool = [v for k,vals in B.items() if k[2]=='bw_old' for v in vals]
print('part A old', len(old7200), rng(old7200), 'med %.3f' % med(old7200), '| pool', len(pool), rng(pool), 'med %.3f' % med(pool), 'width %.3f %%' % ((max(pool)-min(pool))/min(pool)*100))
for r in (1,2):
    s1 = A[(1,r,'bw_new')][0]
    b = B[('A-1',r,'bw_new')]+B[('A-2',r,'bw_new')]
    print(' round', r, 's1', rng(s1), 'vs', rng(b), 'nearest %.2f' % (min(s1)-max(b)))
# all 7200 old within Fig caption
