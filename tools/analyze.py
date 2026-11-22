import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
from collections import defaultdict

d = json.load(open('tracks/港口测试赛道-本科组.json', encoding='utf-8'))
es = d['elements']

rows = defaultdict(list)
for e in es:
    if e['type'] != 'lane':
        continue
    rows[round(e['y'])].append(e)

for y in sorted(rows):
    print(f"\n=== ROW y={y} ===")
    for e in sorted(rows[y], key=lambda e: e['x']):
        print(f"  x={e['x']:7.1f} {e.get('subtype'):15s} w={e['w']:6.1f} h={e['h']:6.1f} rot={e.get('rotation',0)}")

print("\n\n=== NON-LANE ===")
for e in es:
    if e['type'] != 'lane':
        print(f"  {e['id']:16s} {e['type']:9s} {e.get('subtype'):15s} x={e['x']:7.1f} y={e['y']:7.1f} rot={e.get('rotation',0)} props={e.get('props')}")
