# -*- coding: utf-8 -*-
"""提取 PDF 文本（按页分隔），默认输出到 reports/<文件名>.txt。

用法：python tools/extract_pdf.py "data/xxx.pdf" [输出txt路径]
"""
import os
import sys
from pathlib import Path as _P

os.chdir(_P(__file__).resolve().parents[1])

import fitz

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else 'reports/' + _P(src).stem + '.txt'

doc = fitz.open(src)
chunks = []
for i, page in enumerate(doc, 1):
    chunks.append(f"===PAGE {i}===")
    chunks.append(page.get_text())
text = '\n'.join(chunks)

_P(dst).parent.mkdir(parents=True, exist_ok=True)
_P(dst).write_text(text, encoding='utf-8')
print(f"{src} -> {dst}  pages={doc.page_count}  chars={len(text)}")
