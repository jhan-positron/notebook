from PIL import features, ImageFont
print('raqm', features.check('raqm'), 'freetype2', features.check('freetype2'))
F='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts'
f=ImageFont.truetype(f'{F}/IBMPlexSans-400.ttf', 100)
s='Latency: one dependent load, random chain, prefetch defeated. AV To Te'
print('basic', f.getlength(s))
try:
    f2=ImageFont.truetype(f'{F}/IBMPlexSans-400.ttf', 100, layout_engine=ImageFont.Layout.RAQM)
    print('raqm ', f2.getlength(s))
except Exception as e:
    print('raqm err', e)
from fontTools.ttLib import TTFont
t=TTFont(f'{F}/IBMPlexSans-400.ttf'); cmap=t.getBestCmap(); h=t['hmtx']
print('hmtx ', sum(h[cmap[ord(c)]][0] for c in s)/10)
