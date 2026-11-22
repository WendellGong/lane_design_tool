# -*- coding: utf-8 -*-
"""按列打印全部道路元素，便于核对每一列的组成。"""
import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
from collections import defaultdict

P = 'tracks/港口测试赛道-本科组-v2.json'
d = json.load(open(P, encoding='utf-8'))
es = [e for e in d['elements'] if e['type'] == 'lane']

cols = defaultdict(list)
for e in es:
    cols[e['x']].append(e)

for cx in sorted(cols):
    print(f"\n=== x={cx} ===")
    for e in sorted(cols[cx], key=lambda e: e['y']):
        p = e['props']
        extra = ''
        if e['subtype'] in ('crossroads', 't_junction'):
            extra = ' '.join(f"{k}={v}" for k, v in p.items() if k != 'laneW')
        elif e['subtype'] == 'variable_lane':
            extra = f"in={p['lanesIn']} out={p['lanesOut']}"
        print(f"  y={e['y']:8.1f} w={e['w']:6.1f} h={e['h']:6.1f} rot={e.get('rotation', 0):5.1f} "
              f"{e['subtype']:14s} {extra:22s} {e['id']}")
