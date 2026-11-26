import numpy as np
p=np.array([1,2,4,8.0])
avx=np.array([3.95,11.14,35.38,123.11]); amx=np.array([3.14,7.26,18.60,53.50])
print("cuts %",100*(1-amx/avx), "ratios",avx/amx)
# grid over s; for each s linear LSQ for a,b
best={}
for rel in (False,True):
    bb=None
    for s in np.arange(1.5,6.0,0.005):
        X=np.vstack([np.concatenate([p,p]),np.concatenate([p*p,p*p/s])]).T
        y=np.concatenate([avx,amx])
        w=1/y if rel else np.ones_like(y)
        coef,*_=np.linalg.lstsq(X*w[:,None],y*w,rcond=None)
        r=((X@coef-y)*w); sse=(r**2).sum()
        if bb is None or sse<bb[0]: bb=(sse,s,coef)
    print("rel" if rel else "abs","s=%.3f a=%.3f b=%.3f sse=%.4g"%(bb[1],bb[2][0],bb[2][1],bb[0]))
# AVX-only fit then s from each prompt
X=np.vstack([p,p*p]).T
(a,b),*_=np.linalg.lstsq(X,avx,rcond=None)
print("avx-only a,b",a,b,"s per prompt",[b*q*q/(m-a*q) for q,m in zip(p,amx)])
