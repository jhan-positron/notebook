import datetime, zoneinfo
# /proc/stat at 23:47 UTC 21 Oct (inspection === cpu_activity ===), USER_HZ=100 ticks: user nice system idle iowait irq softirq
stat = {120:(357,0,61,10328507,35,41,7),121:(697,0,270,10327918,3,52,16),122:(1696,0,624,10326529,6,137,12),
        123:(1371,0,160,10327375,0,95,3),124:(322,0,238,10328308,29,158,21),125:(350,0,108,10328308,263,75,2),
        126:(692,0,159,10327999,83,113,4),127:(13212,0,51,10315824,0,10,3)}
# arch_timer per CPU since boot at 23:47 UTC 21 Oct: not available per CPU in inspection; use 00:42 UTC values (round4 note in findings) minus 55 min of idle ticks is negligible
at = {120:287784,121:376202,122:1229063,123:896681,124:1410288,125:209949,126:897452,127:54949}
print("hardirq time per CPU since boot (irq column, s), arch_timer count, est. hardirq time per interrupt (us):")
for c in range(120,128):
    irq_s = stat[c][5]/100.0
    print(f"  cpu{c}: irq={irq_s:.2f} s softirq={stat[c][6]/100:.2f} s sys={stat[c][2]/100:.2f} s user={stat[c][0]/100:.2f} s  arch_timer={at[c]:,}  est {1e6*irq_s/at[c]:.2f} us/interrupt")
tz_p = zoneinfo.ZoneInfo("America/Los_Angeles"); tz_e = zoneinfo.ZoneInfo("America/New_York")
for d in ["2026-10-26 01:00", "2026-11-02 01:00", "2026-11-05 01:00"]:
    u = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
    print(d, "UTC ->", u.astimezone(tz_p).strftime("%Y-%m-%d %H:%M %Z"), "/", u.astimezone(tz_e).strftime("%Y-%m-%d %H:%M %Z"))
# DST end date 2026
for day in range(1,8):
    dt = datetime.datetime(2026,11,day,12,tzinfo=tz_p)
    print("2026-11-%02d PT offset" % day, dt.utcoffset())
