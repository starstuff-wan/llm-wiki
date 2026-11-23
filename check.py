# -*- coding: utf-8 -*-
"""构建后自检：内部链接、资源引用、必需要素。"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DOCS = Path(__file__).parent / "docs"
problems, ok = [], 0

for f in sorted(DOCS.glob("*.html")):
    txt = f.read_text(encoding="utf-8")
    for attr in ("href", "src"):
        for m in re.finditer(rf'{attr}="([^"]+)"', txt):
            url = m.group(1)
            if url.startswith(("http", "mailto:", "#", "data:")):
                continue
            target = (f.parent / url.split("#")[0]).resolve()
            if target.exists():
                ok += 1
            else:
                problems.append(f"{f.name}: {attr}={url}")
    for must in ("assets/style.css", "assets/app.js", 'id="sidebar"'):
        if must not in txt:
            problems.append(f"{f.name}: 缺少 {must}")

# 搜索索引与页面是否对应
import json
idx = json.loads((DOCS / "search-index.json").read_text(encoding="utf-8"))
urls = {i["u"] for i in idx}
missing = [u for u in urls if not (DOCS / u).exists()]
problems += [f"search-index 指向不存在的页面: {u}" for u in missing]

print(f"链接/资源校验通过 {ok} 处，问题 {len(problems)} 个")
for p in problems:
    print("  ✗", p)
print("页面数：", len(list(DOCS.glob('*.html'))), "| 索引条目：", len(idx))
