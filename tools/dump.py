import os
from pathlib import Path as _P
os.chdir(_P(__file__).resolve().parents[1])

import json
d = json.load(open('tracks/港口测试赛道-本科组.json', encoding='utf-8'))
es = d['elements']
for e in sorted(es, key=lambda e: (e['y'], e['x'])):
    p = e.get('props', {})
    print(f"{e['id']:14s} {e['type']:9s} {e.get('subtype',''):15s} x={e['x']:7.1f} y={e['y']:7.1f} w={e['w']:6.1f} h={e['h']:6.1f} rot={e.get('rotation',0):6.1f} {p}")
