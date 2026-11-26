import sys
from fontTools.ttLib import TTFont
F='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/fonts'
for w in (400,600):
    f=TTFont(f'{F}/IBMPlexSans-{w}.ttf')
    upm=f['head'].unitsPerEm
    cmap=f.getBestCmap(); hmtx=f['hmtx']
    print('weight',w,'upm',upm,'ascender',f['hhea'].ascent,'descender',f['hhea'].descent,'lineGap',f['hhea'].lineGap)
    print(' OS/2 typo', f['OS/2'].sTypoAscender, f['OS/2'].sTypoDescender, f['OS/2'].sTypoLineGap, 'win', f['OS/2'].usWinAscent, f['OS/2'].usWinDescent)
    print(' digits', [hmtx[cmap[ord(c)]][0] for c in '0123456789'])
    print(' space', hmtx[cmap[ord(' ')]][0], 'a', hmtx[cmap[ord('a')]][0], 'e', hmtx[cmap[ord('e')]][0], 'M', hmtx[cmap[ord('M')]][0])
    for ch in '≥≈−×':
        print('  has', ch, ord(ch) in cmap)
    print(' tables', sorted(f.keys()))
    if 'GSUB' in f:
        feats=sorted({fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord})
        print(' GSUB features', feats)
    if 'GPOS' in f:
        feats=sorted({fr.FeatureTag for fr in f['GPOS'].table.FeatureList.FeatureRecord})
        print(' GPOS features', feats)
