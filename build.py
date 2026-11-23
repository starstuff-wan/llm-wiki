# -*- coding: utf-8 -*-
"""
LLM Wiki 编译器：一份 Markdown → 一个可交互的静态站点。

零第三方依赖，只用标准库。用法：
    python build.py

输入：content/讲解.md
输出：docs/  （index.html + 每个章节一个 .html + graph.html + quiz.html + 资源）
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"
SRC = CONTENT / "讲解.md"

SITE_TITLE = "LLM Wiki"
SITE_SUB = "图像压缩程序 · 代码讲解知识库"

# ── 章节清单：标题关键词 → 文件名 / 侧栏分组 ────────────────────────────────
PAGES = [
    dict(key="先看全局", slug="global", title="全局：三个文件各管什么", group="起步", icon="🗺"),
    dict(key="Huffman 编码", slug="huffman", title="Huffman 编码", group="核心原理", icon="🌲"),
    dict(key="压缩文件格式", slug="format", title="压缩文件格式 ICP1", group="核心原理", icon="📦"),
    dict(key="RLE", slug="rle", title="RLE 行程编码", group="三种算法", icon="➡"),
    dict(key="LZW", slug="lzw", title="LZW 字典编码", group="三种算法", icon="📖"),
    dict(key="图像读写", slug="bmp", title="图像读写：手撕 BMP", group="三种算法", icon="🖼"),
    dict(key="性能指标", slug="metrics", title="性能指标 PSNR / SSIM / 熵", group="质量评估", icon="📐"),
    dict(key="编译与运行", slug="build", title="编译与运行", group="工程实践", icon="⚙"),
    dict(key="我实际验证", slug="evidence", title="验证到什么程度", group="工程实践", icon="✅"),
    dict(key="建议你自己重写", slug="rewrite", title="建议你自己重写的 5 处", group="答辩准备", icon="✍"),
    dict(key="常见追问", slug="faq", title="常见追问速查", group="答辩准备", icon="💬"),
]

# ── 知识图谱连线（双向）：(from, to, 关系) ─────────────────────────────────
EDGES = [
    ("index", "global", "总览"),
    ("global", "huffman", "主算法"),
    ("global", "format", "容器"),
    ("huffman", "format", "码长表写进文件头"),
    ("format", "rle", "同一容器"),
    ("format", "lzw", "同一容器"),
    ("rle", "lzw", "算法对比"),
    ("huffman", "metrics", "平均码长 vs 熵"),
    ("bmp", "global", "输入输出"),
    ("bmp", "format", "原始字节数"),
    ("metrics", "evidence", "实测数据"),
    ("build", "evidence", "编译未验证"),
    ("rewrite", "faq", "答辩问答"),
    ("huffman", "faq", "高频追问"),
    ("lzw", "rewrite", "最易写错"),
]

# ── Markdown 渲染 ──────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return html.escape(s, quote=False)


def inline(text: str) -> str:
    """行内语法：`代码`、**粗体**、*斜体*、[链接](url)。"""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash, text)
    t = esc(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{esc(codes[int(m.group(1))])}</code>", t)
    return t


def code_block(code: str, lang: str) -> str:
    label = lang or "text"
    return (
        '<div class="codeblock">'
        f'<div class="codebar"><span>{esc(label)}</span>'
        '<button class="copy" type="button">复制</button></div>'
        f'<pre><code class="lang-{esc(label)}">{esc(code)}</code></pre>'
        "</div>"
    )


def split_row(row: str):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def table_block(rows, headings):
    out = ['<div class="tablewrap"><table>', "<thead><tr>"]
    for c in headings:
        out.append(f"<th>{inline(c)}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = ' class="num"' if re.fullmatch(r"[\d\s.%:]+", c or "x") else ""
            out.append(f"<td{cls}>{inline(c)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def md_to_html(md: str):
    """返回 (html, headings)。headings 供目录使用。"""
    lines = md.split("\n")
    out, heads = [], []
    i, n = 0, len(lines)
    hid = 0
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        # 代码块
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(code_block("\n".join(buf), lang))
            continue
        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            hid += 1
            aid = f"h{hid}"
            if lvl <= 3:
                heads.append((lvl, aid, re.sub(r"[`*]", "", txt)))
            out.append(f'<h{lvl} id="{aid}">{inline(txt)}</h{lvl}>')
            i += 1
            continue
        # 分隔线
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            out.append("<hr>")
            i += 1
            continue
        # 表格
        if s.startswith("|") and i + 1 < n and re.fullmatch(r"\|[\s:|-]+\|?", lines[i + 1].strip()):
            heads_row = split_row(s)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append(table_block(rows, heads_row))
            continue
        # 引用块 → 提示卡
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f'<div class="callout"><span class="ci">💡</span><p>{inline(" ".join(buf))}</p></div>')
            continue
        # 列表
        if re.match(r"^([-*]|\d+\.)\s+", s):
            ordered = bool(re.match(r"^\d+\.", s))
            items = []
            while i < n and re.match(r"^([-*]|\d+\.)\s+", lines[i].strip()):
                txt = re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip())
                items.append(txt)
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            continue
        # 段落
        buf = []
        while i < n:
            t = lines[i].strip()
            if (not t or t.startswith("```") or t.startswith("|") or t.startswith(">")
                    or re.match(r"^#{1,6}\s", t) or re.match(r"^([-*]|\d+\.)\s+", t)
                    or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", t)):
                break
            buf.append(t)
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "".join(out), heads


def plain(md: str) -> str:
    t = re.sub(r"```.*?```", " ", md, flags=re.S)
    t = re.sub(r"[#>*`|_\-]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ── 拆章节 ────────────────────────────────────────────────────────────────
def split_sections(md: str):
    intro, sections, cur = [], [], None
    for line in md.split("\n"):
        if line.startswith("## "):
            cur = [line[3:].strip(), []]
            sections.append(cur)
        elif cur is None:
            intro.append(line)
        else:
            cur[1].append(line)
    return "\n".join(intro), [(t, "\n".join(b)) for t, b in sections]


def clean_title(t: str) -> str:
    return re.sub(r"^\d+\.\s*", "", t).strip()


def tidy(md: str, drop_h1: bool = False) -> str:
    """去掉章节末尾的分隔线，首页还要去掉重复的 H1。"""
    lines = md.strip().split("\n")
    if drop_h1 and lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and (not lines[-1].strip() or re.fullmatch(r"-{3,}", lines[-1].strip())):
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


# ── 页面模板 ──────────────────────────────────────────────────────────────
NAV_ORDER = ["index"] + [p["slug"] for p in PAGES]


def nav_html(active: str) -> str:
    groups, order = {}, []
    for p in PAGES:
        if p["group"] not in groups:
            groups[p["group"]] = []
            order.append(p["group"])
        groups[p["group"]].append(p)
    out = ['<nav class="nav">']
    out.append(
        f'<a class="navlink {"active" if active == "index" else ""}" href="index.html">'
        '<span class="ni">◈</span>首页总览</a>'
    )
    for g in order:
        out.append(f'<div class="navgroup"><h5>{g}</h5>')
        for p in groups[g]:
            cls = "navlink active" if p["slug"] == active else "navlink"
            out.append(f'<a class="{cls}" href="{p["slug"]}.html"><span class="ni">{p["icon"]}</span>{esc(p["title"])}</a>')
        out.append("</div>")
    out.append('<div class="navgroup"><h5>互动</h5>')
    out.append(f'<a class="navlink {"active" if active == "graph" else ""}" href="graph.html"><span class="ni">🕸</span>知识图谱</a>')
    out.append(f'<a class="navlink {"active" if active == "quiz" else ""}" href="quiz.html"><span class="ni">🎯</span>自测卡片</a>')
    out.append("</div></nav>")
    return "".join(out)


def page_html(title: str, body: str, active: str, toc: str = "", related: str = "", pager: str = "") -> str:
    toc_block = f'<aside class="toc"><h4>本页目录</h4><ul>{toc}</ul></aside>' if toc else '<aside class="toc"></aside>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {SITE_TITLE}</title>
<meta name="description" content="{esc(SITE_SUB)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%234f46e5'/%3E%3Ctext x='16' y='23' font-size='17' text-anchor='middle' fill='white'%3E%23%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="assets/style.css">
<script>try{{var q=new URLSearchParams(location.search).get('theme');var t=q||localStorage.getItem('llmwiki-theme');if(t)document.documentElement.dataset.theme=t;else if(matchMedia('(prefers-color-scheme: dark)').matches)document.documentElement.dataset.theme='dark';}}catch(e){{}}</script>
</head>
<body>
<div class="progress"><i id="progressBar"></i></div>
<header class="topbar">
  <button class="icon-btn only-mobile" id="menuBtn" aria-label="打开菜单">☰</button>
  <a class="brand" href="index.html"><span class="logo">◈</span><span>{SITE_TITLE}</span></a>
  <button class="search-trigger" id="searchTrigger"><span>🔍 搜索全部页面</span><kbd>Ctrl</kbd><kbd>K</kbd></button>
  <button class="icon-btn" id="themeBtn" aria-label="切换主题">🌙</button>
</header>
<div class="layout">
  <aside class="sidebar" id="sidebar">{nav_html(active)}</aside>
  <main class="content"><article>{body}</article>{related}{pager}</main>
  {toc_block}
</div>
<div class="scrim" id="scrim"></div>
<div class="palette" id="palette" hidden>
  <div class="pbox">
    <input id="searchInput" type="text" placeholder="输入关键词，↑↓ 选择，Enter 打开…" autocomplete="off">
    <div class="presults" id="searchResults"></div>
    <div class="pfoot"><span><kbd>Esc</kbd> 关闭</span><span><kbd>↑</kbd><kbd>↓</kbd> 移动</span><span><kbd>Enter</kbd> 打开</span></div>
  </div>
</div>
<script src="assets/app.js"></script>
</body>
</html>
"""


def toc_from(heads):
    items = [f'<li><a href="#{aid}">{esc(txt)}</a></li>' for lvl, aid, txt in heads if lvl == 3]
    return "".join(items)


def related_html(slug: str, titles: dict) -> str:
    rel = []
    for a, b, why in EDGES:
        if a == slug:
            rel.append((b, why))
        elif b == slug:
            rel.append((a, why))
    if not rel:
        return ""
    chips = "".join(
        f'<a class="chip" href="{("index" if s == "index" else s) + ".html"}">{esc(titles.get(s, s))}'
        f'<em>{esc(why)}</em></a>'
        for s, why in rel
    )
    return f'<section class="related"><h4>相关页面</h4><div class="chips">{chips}</div></section>'


def pager_html(slug: str, titles: dict) -> str:
    if slug == "index":
        return ""
    try:
        k = NAV_ORDER.index(slug)
    except ValueError:
        return ""
    prev_s = NAV_ORDER[k - 1] if k > 0 else None
    next_s = NAV_ORDER[k + 1] if k + 1 < len(NAV_ORDER) else None
    left = (f'<a class="pg prev" href="{prev_s}.html"><small>← 上一篇</small>{esc(titles[prev_s])}</a>'
            if prev_s else "<span></span>")
    right = (f'<a class="pg next" href="{next_s}.html"><small>下一篇 →</small>{esc(titles[next_s])}</a>'
             if next_s else "<span></span>")
    return f'<nav class="pager">{left}{right}</nav>'


# ── 构建 ──────────────────────────────────────────────────────────────────
def main():
    md = SRC.read_text(encoding="utf-8")
    intro_md, sections = split_sections(md)

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for f in (ROOT / "assets").iterdir():
        if f.is_file():
            shutil.copy(f, OUT / "assets" / f.name)

    titles = {"index": "首页总览"}
    for p in PAGES:
        titles[p["slug"]] = p["title"]

    # 章节标题 → 页面配置
    used = []
    for title, body in sections:
        ct = clean_title(title)
        match = next((p for p in PAGES if p["key"] in ct), None)
        if not match:
            raise SystemExit(f"未匹配到章节：{title}")
        used.append((match, body, ct))

    search = []
    for p, body, ct in used:
        body = tidy(body)
        body_html, heads = md_to_html(body)
        body_full = (
            f'<div class="pagehead"><div class="kicker">{esc(p["group"])}</div>'
            f'<h1>{esc(p["title"])}</h1></div>' + body_html
        )
        html_out = page_html(
            p["title"], body_full, p["slug"],
            toc="".join(f'<li><a href="#{aid}">{esc(t)}</a></li>' for _, aid, t in heads),
            related=related_html(p["slug"], titles),
            pager=pager_html(p["slug"], titles),
        )
        (OUT / f'{p["slug"]}.html').write_text(html_out, encoding="utf-8")
        search.append({"t": p["title"], "u": f'{p["slug"]}.html', "g": p["group"], "x": plain(body)[:3000]})

    # 首页
    intro_html, _ = md_to_html(tidy(intro_md, drop_h1=True))
    cards = "".join(
        f'<a class="card" href="{p["slug"]}.html"><span class="ci">{p["icon"]}</span>'
        f'<b>{esc(p["title"])}</b><small>{esc(p["group"])}</small></a>'
        for p in PAGES
    )
    wc = len(re.sub(r"\s", "", intro_md + "".join(b for _, b in sections)))
    idx_body = f"""<div class="hero">
  <div class="kicker">{SITE_SUB}</div>
  <h1>从一份 Markdown 长文，到一个能点、能搜、能联想的 wiki</h1>
  <p class="lede">共 {len(PAGES)} 个词条 · {wc:,} 字 · 由 build.py 自动编译。左侧是目录，右上角可全局搜索（Ctrl K），
  🕸 知识图谱可以拖动节点，🎯 自测卡片可以边翻边背。</p>
  <div class="herobtns"><a class="btn primary" href="global.html">从「全局」开始读 →</a><a class="btn" href="graph.html">打开知识图谱</a></div>
</div>
<div class="quote">{intro_html}</div>
<h2 class="sec">全部词条</h2>
<div class="cards">{cards}</div>"""
    (OUT / "index.html").write_text(page_html("首页总览", idx_body, "index"), encoding="utf-8")
    search.insert(0, {"t": "首页总览", "u": "index.html", "g": "起步", "x": plain(intro_md)[:3000]})

    (OUT / "search-index.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    # 知识图谱数据
    nodes = [{"id": "index", "t": "首页总览", "g": "起步", "w": 4}]
    for p in PAGES:
        nodes.append({"id": p["slug"], "t": p["title"], "g": p["group"], "w": 5})
    nodes.append({"id": "graph", "t": "知识图谱", "g": "互动", "w": 3})
    nodes.append({"id": "quiz", "t": "自测卡片", "g": "互动", "w": 3})
    edges = [{"s": a, "t": b, "l": w} for a, b, w in EDGES]
    edges += [{"s": "index", "t": "graph", "l": "互动"}, {"s": "index", "t": "quiz", "l": "互动"},
              {"s": "faq", "t": "quiz", "l": "出题"}]
    graph_data = {"nodes": nodes, "edges": edges}

    graph_body = f"""<div class="pagehead"><div class="kicker">互动</div><h1>知识图谱</h1>
<p class="lede">拖动节点可以移动，点节点打开对应页面。节点大小代表内容量，连线上的字是两页之间的关系。</p></div>
<div class="graphwrap"><svg id="graphSvg"></svg><div class="glegend" id="glegend"></div></div>
<script type="application/json" id="graph-data">{json.dumps(graph_data, ensure_ascii=False)}</script>"""
    (OUT / "graph.html").write_text(
        page_html("知识图谱", graph_body, "graph", pager=""), encoding="utf-8"
    )

    # 测验：从「常见追问」表格抽 Q/A
    quiz_items = []
    for p, body, _ in used:
        if p["slug"] != "faq":
            continue
        rows = [l for l in body.split("\n") if l.strip().startswith("|")]
        for r in rows[2:]:
            cells = split_row(r)
            if len(cells) >= 2:
                quiz_items.append((cells[0], cells[1]))

    cards = "".join(
        f'<div class="qcard" tabindex="0" data-i="{k}">'
        f'<span class="qtag">Q{k + 1}</span>'
        f'<span class="q">{inline(q)}</span>'
        f'<span class="a">{inline(a)}</span>'
        f'<span class="hint">点一下看答案</span>'
        f'<span class="mark">我会了</span></div>'
        for k, (q, a) in enumerate(quiz_items)
    )
    quiz_body = f"""<div id="quizPage"><div class="pagehead"><div class="kicker">互动</div><h1>自测卡片</h1>
<p class="lede">答辩前用这个过一遍：点卡片翻答案，会记分。共 {len(quiz_items)} 题，来自「常见追问速查」。</p>
<div class="scorebar">已翻 <b id="done">0</b> / {len(quiz_items)} · 标记「会了」<b id="known">0</b>
<button class="btn small" id="resetQuiz" type="button">重置</button></div></div>
<div class="qgrid">{cards}</div></div>"""
    (OUT / "quiz.html").write_text(
        page_html("自测卡片", quiz_body, "quiz", pager=""), encoding="utf-8"
    )

    print(f"✅ 构建完成：{len(list(OUT.glob('*.html')))} 个页面 → {OUT}")
    print(f"   测验题 {len(quiz_items)} 道，搜索条目 {len(search)} 条")


if __name__ == "__main__":
    main()
