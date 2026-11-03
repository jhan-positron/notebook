H=open('/home/jhan/workspace/titan/rampup/jeremy-tasks-plan.html',encoding='utf-8').read()
T=open('plan_text.txt',encoding='utf-8').read()
for q in ["Fallback slot: Friday 13:00 UTC.","ends with the reboot. Fallback slot: Friday 13:00 UTC.","are owned by uid 1001.","Security: 347 files under","Change the drop-in to identical CPU lists, which the kernel requires:","P1c. Remove the expedited-RCU IPIs now","; 126-127 applied by default","Both observations match the host.","neither blocks the reboot","last three boots (3, 5 and 20 October)"]:
    print(f"HTML={H.count(q)} TXT={T.count(q)} :: {q}")
