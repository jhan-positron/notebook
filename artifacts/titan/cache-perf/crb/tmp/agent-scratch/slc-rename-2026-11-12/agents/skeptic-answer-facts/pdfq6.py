import fitz, re
trm='/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
def norm(s): return re.sub(r'\s+',' ',s).replace('ﬁ','fi').replace('ﬂ','fl').replace('ﬀ','ff').replace('ﬃ','ffi')
d=fitz.open(trm)
t=norm(d[16].get_text())
i=t.find('device ports for connecting')
print('p17:', t[max(0,i-200):i+120] if i>=0 else 'NOT FOUND')
t=norm(d[26].get_text())
i=t.find('256B flit support for PCIe')
print('p27:', t[max(0,i-200):i+120] if i>=0 else 'NOT FOUND')
