import re, sys, cairosvg, os
html=open('/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html').read()
out=sys.argv[1]; os.makedirs(out, exist_ok=True)
figs=re.findall(r'<figure id="(fig\d+)">.*?(<svg.*?</svg>)', html, flags=re.S)
for fid, svg in figs:
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f'{out}/{fid}.png', output_width=1300)
print(len(figs), 'figures rendered:', ' '.join(f for f,_ in figs))
