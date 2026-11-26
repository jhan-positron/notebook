import re,sys,subprocess
A,ids=sys.argv[1],sys.argv[2:]
d=open(A+'/new.dom.html').read()
for i in ids:
    m=re.search(r'<svg id="%s" viewBox="0 0 (\d+) (\d+)".*?</svg>'%i,d,re.S)
    w,h=int(m.group(1)),int(m.group(2)); k=1.5
    svg=m.group(0).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" style="font-family:IBM Plex Sans,sans-serif;background:#fff" '%(w*k,h*k),1)
    open(f'{A}/{i}.html','w').write('<!doctype html><body style="margin:0">'+svg)
    subprocess.run([A+'/render.sh',f'{A}/{i}.html','--hide-scrollbars',f'--window-size={int(w*k)},{int(h*k)}',f'--screenshot={A}/{i}.png'],stderr=subprocess.DEVNULL)
    print(i,w,h)
