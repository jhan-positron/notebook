import sys
p="build_plan.py"; s=open(p,encoding="utf-8").read()
R=[]
def rep(o,n): R.append((o,n))
rep("1. Your account, keys, toolchain and disk are in place, and your logins from the laptop and from sw-dev-01\n   worked. I take the 21 Oct sessions from alpha (192.168.1.200) and the churn-r1 run to be yours as well.\n   Tell me if not. The churn-r1 record is on the host.",
    "1. Your account, keys, toolchain and disk are in place, and your logins from the laptop and from sw-dev-01\n   worked. I take the 21 Oct sessions from alpha (192.168.1.200), and the run of the churn latency label they\n   made (record directory ~/positron/runs/churn-r1), to be yours as well. Tell me if not.")
rep("4. nohz_full and rcu_nocbs are not possible on the running kernel (built without CONFIG_NO_HZ_FULL) and are\n   not expected by Friday. They need a rebuilt kernel, which I have requested from Arm. Until then a busy\n   isolated core keeps the 250 Hz timer tick (one interrupt every 4 ms, about 1-2 us each).",
    "4. nohz_full and rcu_nocbs are not possible on the running kernel (built without CONFIG_NO_HZ_FULL). We need to\n   rebuild the custom kernel. Dan requested ARM to grant me access to their github. Until we rebuild a new\n   kernel, a busy isolated core keeps the 250 Hz timer tick (one interrupt every 4 ms, about 1-2 us each).")
rep("5. churn-r1 was voided because the fake device's MEAN lateness (6.25 us) exceeded the 2.5 us band, not by\n   missing isolation. The host clock alone does not explain it: your hiccup probe in sleep mode on an idle\n   core under schedutil gives mean lateness 0.02 us (0 of 2000 cycles over 2.5 us). During churn-r1 the device\n   thread shared cores 120-126 with the other threads,",
    "5. That 21 Oct run was voided because the fake device's MEAN lateness (6.25 us) exceeded the 2.5 us band, not\n   by missing isolation. The host clock alone does not explain it: your hiccup probe in sleep mode on an idle\n   core under schedutil gives mean lateness 0.02 us (0 of 2000 cycles over 2.5 us). During that run the device\n   thread shared cores 120-126 with the other threads,")
rep("   for a before/after late_mean comparison with churn-r1? Default: no.", "   for a before/after late_mean comparison with the 21 Oct run? Default: no.")
rep("Updated 22 October 06:00 UTC with Jibin's answers and the as-built state.", "Updated 22 October 06:20 UTC with Jibin's answers, the as-built state, and Jibin's own wording of items 4 and 5.")
# A6 and the kernel-source status elsewhere
rep('""" + OPENQ + """ Jibin has asked Arm. Is it blocking?', '""" + OPENQ + """ Dan asked Arm to grant Jibin access to Arm\'s GitHub, so that Jibin can rebuild the kernel from source (answer pending). Is it blocking?')
rep("<li>Asked on 22 October (A6, answer pending): Arm's SVK contact, for the kernel tree at commit <code>4dbc8bb88858</code> with its config, or for a build with <code>CONFIG_NO_HZ_FULL=y</code>.</li>",
    "<li>Kernel source (A6): Dan asked Arm on 22 October to grant Jibin access to Arm's GitHub, so that the vendor kernel at commit <code>4dbc8bb88858</code> can be rebuilt with <code>CONFIG_NO_HZ_FULL=y</code>. Answer pending.</li>")
rep("Owner: Arm (the kernel's builder), then the administrator. Reboot: a second one.", "Owner: Jibin, once Arm grants the GitHub access that Dan requested on 22 October (path A below), then the administrator for the install. Reboot: a second one.")
rep("<li>Who at Arm can provide the vendor kernel's source at <code>4dbc8bb88858</code> or a NO_HZ_FULL build, and by when. Source: the SVK contact, asked by Jibin on 22 October (A6).</li>",
    "<li>When Arm grants the GitHub access that Dan requested on 22 October, and whether the tree at <code>4dbc8bb88858</code> with its config is in it (A6).</li>")
rep('    ("alpha", "The LAN host 192.168.1.200', '    ("Dan", "Jibin\'s colleague who asked Arm on 22 October to grant Jibin access to Arm\'s GitHub, for the kernel source (A6)."),\n    ("alpha", "The LAN host 192.168.1.200')
rep("revised 22 October 02:40, 05:05 and 06:00 UTC (as-built).", "revised 22 October 02:40, 05:05, 06:00 (as-built) and 06:20 UTC.")
miss=[(o,s.count(o)) for o,n in R if s.count(o)!=1]
if miss:
    print("NOT APPLIED:"); [print(f"  count={c}: {o[:100]!r}") for o,c in miss]; sys.exit(1)
for o,n in R: s=s.replace(o,n)
open(p,"w",encoding="utf-8").write(s); print(f"applied {len(R)}")
