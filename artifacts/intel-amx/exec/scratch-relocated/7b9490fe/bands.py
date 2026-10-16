import re
arm = {}
pairs = []
with open('/home/jhan/workspace/intel-AMX/exec/results/pr3-E-cpu/summary.md') as f:
    for line in f:
        parts = [p.strip() for p in line.strip().strip('|').split('|')]
        if len(parts) == 14 and parts[0].startswith('q3-'):
            cell, _, _, _, _, armname, n, tps, sd, ttft, tsd = parts[:11]
            arm[(cell, armname)] = (float(tps), float(sd), float(ttft), float(tsd))
        elif len(parts) == 8 and parts[0].startswith('q3-'):
            pairs.append(parts)
print("cell | pair | TPS% recomputed | TTFT% recomputed | TTFT ms recomputed | band TPS | band TTFT | tps verdict | ttft verdict")
for p in pairs:
    cell, _, comp, tpsp, ttftp, ttftms, ptps, pttft = p
    a, b = comp.split(' vs ')
    A = arm[(cell, a)]; B = arm[(cell, b)]
    dtps = A[0] - B[0]; dttft = A[2] - B[2]
    tpspct = 100 * dtps / B[0]; ttftpct = 100 * dttft / B[2]
    band_tps = max(2 * max(A[1], B[1]), 0.4)
    band_ttft = max(2 * max(A[3], B[3]), 0.15)
    # paired deltas from the file
    m = re.match(r'([+-][\d.]+) \(([\d.]+), (\d), ([+-][\d.]+)\)', ptps)
    pd_tps = float(m.group(1))
    m2 = re.match(r'([+-]\d+) \((\d+), (\d), ([+-][\d.]+)\)', pttft)
    pd_ttft = int(m2.group(1))
    v_tps = 'beyond' if abs(pd_tps) > band_tps else 'inside'
    v_ttft = 'beyond' if abs(pd_ttft)/1000 > band_ttft else 'inside'
    print(f"{cell} | {comp} | {tpspct:+.2f} (file {tpsp}) | {ttftpct:+.2f} (file {ttftp}) | {dttft*1000:+.1f} (file {ttftms}) | {band_tps:.2f} | {band_ttft:.2f} | {pd_tps:+.2f} {v_tps} | {pd_ttft:+d} ms {v_ttft}")
