import math
def betacf(a,b,x):
    MAXIT=300; EPS=3e-14; FPMIN=1e-300
    qab=a+b; qap=a+1; qam=a-1; c=1.0; d=1-qab*x/qap
    if abs(d)<FPMIN: d=FPMIN
    d=1/d; h=d
    for m in range(1,MAXIT+1):
        m2=2*m; aa=m*(b-m)*x/((qam+m2)*(a+m2))
        d=1+aa*d; d=FPMIN if abs(d)<FPMIN else d; c=1+aa/c; c=FPMIN if abs(c)<FPMIN else c; d=1/d; h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d=1+aa*d; d=FPMIN if abs(d)<FPMIN else d; c=1+aa/c; c=FPMIN if abs(c)<FPMIN else c; d=1/d; de=d*c; h*=de
        if abs(de-1)<EPS: break
    return h
def betai(a,b,x):
    if x<=0: return 0.0
    if x>=1: return 1.0
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log(1-x))
    if x<(a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1-bt*betacf(b,a,1-x)/b
def p2(t,df): return betai(df/2,0.5,df/(df+t*t))
print("sanity t=2 df=10:",round(p2(2,10),4),"t=12.706 df=1:",round(p2(12.706,1),4),"t=4.303 df=2:",round(p2(4.303,2),4), "t=3.9 df=1 cauchy exact:", round(2*(0.5-math.atan(3.9)/math.pi),4))
for lbl,t,df in [("wedperf tp4 VNNI-K +6.1%",3.9,1.0),("wedperf tp2 VNNI-K +2.0%",6.4,1.1),("wedperf tp4 AVX -7.7%",-10.9,1.1),("wedperf tp2 AVX -19.1%",-52.4,1.0),("CI tp4 canon -1.9%",-5.7,2.4),("CI tp2 canon +4.6%",14.0,3.9),("attr tp2 canon +1.2%",8.2,5.9),("attr tp2 VNNI-K +2.3%",10.6,5.9),("attr tp4 canon vs avx under FPGA +1.6%",3.7,10.0),("attr tp2 vnnik vs avx under FPGA -1.7%",-4.7,8.6),("attr tp2 canon vs avx under FPGA -0.6%",-1.8,7.1),("attr tp4 vnnik vs avx under FPGA -1.0%",-1.9,9.0)]:
    print(f"{lbl:45s} t {t:+.1f} df {df:.1f} two-sided p {p2(abs(t),df):.3f}")
# exact welch t/df for wedperf tp4 vnnik using per-rep values
import statistics as st
a=[2217.9,2285.1]; b=[2126.0,2112.6,2124.7]
va=st.stdev(a)**2/2; vb=st.stdev(b)**2/3
t=(st.mean(a)-st.mean(b))/math.sqrt(va+vb); df=(va+vb)**2/(va**2/1+vb**2/2)
print("wedperf tp4 vnnik exact: t",round(t,2),"df",round(df,2),"p",round(p2(t,df),3), "; FPGA reps differ by", a[1]-a[0], "ms")
