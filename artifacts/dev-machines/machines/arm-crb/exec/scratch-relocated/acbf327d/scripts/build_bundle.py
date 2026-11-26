"""Copy the evidence files that the report cites into one zip, with names an outside reader can follow."""
import hashlib, os, re, shutil, sys, zipfile

results = os.path.expanduser("~/workspace/titan/cache-perf/crb/results")
stage = sys.argv[1]
out_zip = sys.argv[2]

if os.path.exists(stage):
    shutil.rmtree(stage)

MONTH = {"Sep": "09", "Oct": "10", "Nov": "11"}
plan = []  # (source path, name inside the zip)

# Kernel logs of the 12 boots at 8000 MT/s. k-11.txt is the oldest boot, k0.txt the newest.
for n, rel in enumerate(range(-11, 1), start=1):
    src = f"{results}/dimm-check-20261117/k{rel}.txt"
    with open(src, errors="replace") as f:
        text = f.read()
    first = text.splitlines()[0]
    m = re.match(r"(\w{3}) (\d{2}) (\d{2}):(\d{2}):\d{2} ", first)
    mon, day, hh, mm = m.groups()
    count = re.search(r"This system has (\d+) DIMM sockets", text).group(1)
    name = f"kernel-logs-8000MTs/boot{n:02d}_2026-{MONTH[mon]}-{day}T{hh}{mm}Z_{count}-modules.txt"
    plan.append((src, name))

plan += [
    (f"{results}/dmidecode-t17-2026-10-30.txt",
     "module-lists/dmidecode-t17_2026-10-30_10-modules_8000MTs.txt"),
    (f"{results}/dimm-check-20261117/dmi17-062957.txt",
     "module-lists/dmidecode-t17_2026-11-17T0629Z_12-modules_8000MTs.txt"),
    (f"{results}/dimm-check-20261117/dmi16-19.txt",
     "module-lists/dmidecode-t16-t19_2026-11-17T0629Z_12-modules_8000MTs.txt"),
    (f"{results}/dimm7200-20261117/dmi17-7200.txt",
     "module-lists/dmidecode-t17_2026-11-17_12-modules_7200MTs.txt"),
    (f"{results}/dimm7200-20261117/dmi2.txt",
     "module-lists/dmidecode-t2_motherboard.txt"),
    (f"{results}/uefisettings-20261117/identify.txt",
     "firmware/uefisettings-identify.txt"),
    (f"{results}/uefisettings-20261117/questions.json",
     "firmware/uefisettings-settings-list_8000MTs.json"),
    (f"{results}/dimm7200-20261117/set.txt",
     "test-7200MTs/uefisettings-set-reply.txt"),
]
for i in range(1, 7):
    plan.append((f"{results}/dimm7200-20261117/try{i}.txt", f"test-7200MTs/reboot-try{i}.txt"))

for src, name in plan:
    dst = os.path.join(stage, name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)

os.makedirs(os.path.dirname(out_zip), exist_ok=True)
with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, name in plan:
        z.write(os.path.join(stage, name), name)

for src, name in plan:
    print(f"{os.path.getsize(src):>9}  {name}   <- {os.path.relpath(src, results)}")
h = hashlib.sha256(open(out_zip, "rb").read()).hexdigest()
print("files:", len(plan))
print("zip bytes:", os.path.getsize(out_zip))
print("zip sha256:", h)
