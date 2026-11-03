# Numbers from the evidence files (see comments) -> rates and shares for the findings.
# inspection.txt "interrupts": per-CPU sum over all IRQ lines at 23:47 UTC 21 Oct (cumulative since boot 19:06 UTC 20 Oct)
cum_2347 = {120:300493,121:391110,122:1252963,123:905910,124:1432061,125:235026,126:910757,127:58972}
# round4.txt churn_r1_job_log: isol.py diff irqs_each_watch over seconds=172.9 (job 18:32-18:35 UTC 21 Oct)
job = {120:255378,121:277078,122:1133890,123:885004,124:1324691,125:222394,126:871614,127:40859}
busy = {120:0.0153,121:0.049,122:0.1214,123:0.0829,124:0.0314,125:0.026,126:0.0516,127:0.7609}
secs = 172.9
HZ = 250
tot_cum = sum(cum_2347.values()); tot_job = sum(job.values())
print(f"cumulative interrupts on 120-127 at 23:47 UTC: {tot_cum:,}; during churn-r1 (172.9 s): {tot_job:,} = {100*tot_job/tot_cum:.1f} %")
print("per CPU during the job: interrupts, rate/s, max tick-rate explained by busy share (busy*250/s), excess rate = hrtimer-style wakeups")
for c in range(120,128):
    rate = job[c]/secs
    tickmax = busy[c]*HZ
    print(f"  cpu{c}: {job[c]:>9,} irqs  {rate:8.1f}/s  busy {100*busy[c]:5.1f}%  tick<= {tickmax:6.1f}/s  excess ~{rate-tickmax:8.1f}/s")
# arch_timer line only, 120-127 cumulative: 5,327,444 at 23:47 (inspection)
arch_timer_2347 = 5327444; ipi1_2347 = 123695; ipi0_2347 = 2032; ipi5_2347=329
nvme_2347 = 22045+6850+2516+1061+379+233+199+144+74+32+1*6
print(f"share of cumulative 120-127 interrupts that are arch_timer: {100*arch_timer_2347/tot_cum:.1f} %  (IPI1 {100*ipi1_2347/tot_cum:.2f} %, nvme {100*nvme_2347/tot_cum:.2f} %, IPI0 {100*ipi0_2347/tot_cum:.3f} %)")
print(f"lower bound on arch_timer interrupts during the job: {tot_job - ipi1_2347 - nvme_2347 - ipi0_2347 - ipi5_2347:,} (job total minus every non-timer count since boot)")
# idle tick: inspection 5 s delta over 8 idle CPUs: arch_timer 200, IPI1 3; round3: cpu121 idle 5 s: 10 ticks; busy 5 s: 1261 (cpu125: 1258)
print(f"idle: {200/5/8:.1f} arch_timer/s per CPU (8-CPU 5 s sample); cpu121 alone {10/5:.1f}/s; busy pinned spin: {1261/5:.1f}/s (cpu125 {1258/5:.1f}/s) vs HZ={HZ}")
print(f"idle IPI1: {3/5/8:.3f}/s per CPU; busy cpu121: {1/5:.1f}/s")
# IPI1 between 23:47 and 00:42 UTC (55 min): 123,695 -> 132,061 on 120-127
d = 132061-123695; print(f"IPI1 on 120-127 between 23:47 and 00:42 UTC (55 min, inspections running): {d:,} = {d/55/60:.2f}/s over 8 CPUs")
# uptime at 00:42:46 UTC: 106739.69 s; arch_timer per CPU then
at = {120:287784,121:376202,122:1229063,123:896681,124:1410288,125:209949,126:897452,127:54949}
up = 106739.69
print("arch_timer per CPU since boot (00:42 UTC) and average rate /s: " + ", ".join(f"cpu{c}={v:,} ({v/up:.1f}/s)" for c,v in at.items()))
# /proc/stat user ticks (USER_HZ=100) on cpu127 at 23:47: 13212 -> 132.1 s user time since boot; job busy on 127: 0.7609*172.9
print(f"cpu127 user time since boot (23:47): {13212/100:.1f} s; churn-r1 busy on cpu127: {0.7609*secs:.1f} s -> {100*0.7609*secs/(13212/100):.0f} % of cpu127's lifetime user time was the churn job")
