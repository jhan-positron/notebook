import sys, difflib, re
A = open('/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html', encoding='utf-8').read().split('\n')
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read().split('\n')
print(len(A), len(B))
changed = [i for i in range(min(len(A), len(B))) if A[i] != B[i]]
print("changed lines:", len(changed))
print([i+1 for i in changed])
