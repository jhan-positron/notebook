import os, sys, re, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import *
_cache = {}
def value_at(relpath, line):
    """value of the interval whose row (I row for bwx, csv row for bandwidth.c) is at 'line' of R/relpath. Own parse."""
    path = os.path.join(R, relpath)
    if path not in _cache:
        first = open(path).readline()
        if first.startswith('-- '):
            d = {}
            for p in parse_bw(path):
                for i in p['iv']:
                    d[i['line']] = dict(v=i['agg'], hdr=p['hdr'], hline=p['line'], passes=i['passes'], kernel=i['kernel'], rep=i['rep'])
            _cache[path] = d
        else:
            d = {}
            ivs = parse_bwx(path)
            for n, i in enumerate(ivs):
                prev = ivs[n-1]['kernel'] if n > 0 else None
                d[i['line_I']] = dict(v=i['total'], kernel=i['kernel'], round=i['round'], pos=i['pos'], n=i['n'], prev=prev, I_agg=i['I_agg'], first_T=i['first_T'], last_T=i['last_T'])
            _cache[path] = d
    return _cache[path][line]
