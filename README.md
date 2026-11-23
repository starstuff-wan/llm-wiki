# LLM Wiki · 图像压缩代码讲解知识库

把 `content/讲解.md` 一份 Markdown 长文，编译成一个可交互的静态 wiki 站点：
**全局搜索、知识图谱（可拖动）、自测卡片、暗色模式、代码复制、目录跟随**。

零第三方依赖，只用 Python 标准库。

## 目录结构

```
llmwiki-site/
├─ content/讲解.md      ← 你的 Markdown 原文（要改内容只改这里）
├─ build.py             ← 编译器：md → 多页 HTML + 搜索索引 + 图谱数据 + 测验卡
├─ check.py             ← 构建后自检（内部链接 / 资源 / 索引一致性）
├─ assets/style.css     ← 样式（配色、暗色主题都在 :root 变量里）
├─ assets/app.js        ← 交互（搜索、图谱力导向布局、卡片计分、快捷键）
└─ docs/                ← 构建产物（GitHub Pages 就发布这个目录）
   ├─ index.html  global.html  huffman.html …  共 12 个内容页
   ├─ graph.html  quiz.html
   ├─ assets/  search-index.json  .nojekyll
```

## 本地跑起来

```powershell
cd llmwiki-site
python build.py                                   # 生成 docs/
python -m http.server 8765 --directory docs       # 起本地服务器
# 浏览器打开 http://127.0.0.1:8765
```

> 必须用 http 打开，不要双击 `docs/index.html`。搜索索引是用 `fetch` 读的，
> `file://` 协议下会被浏览器拦住，图谱和搜索会失效。

## 改内容

1. 编辑 `content/讲解.md`。`## 二级标题` 会自动变成一个页面。
2. 新加章节时，在 `build.py` 顶部的 `PAGES` 列表里加一行（关键词要能在标题里匹配到）：

```python
dict(key="你的标题关键词", slug="my-page", title="页面显示名", group="分组名", icon="🧩"),
```

3. `python build.py` 重新生成。侧栏、翻页、搜索索引、图谱节点会自动更新。
4. 想加"两页之间的关系"，往 `build.py` 的 `EDGES` 里加一条：`("a", "b", "关系说明")`。

## 改样子

`assets/style.css` 开头是设计变量：

```css
:root { --accent: #4f46e5; --sidebar-w: 248px; --radius: 14px; }
[data-theme="dark"] { --accent: #8b93ff; }
```

改 `--accent` 一处，全站主色跟着变。

## 发布到 GitHub Pages

站点必须从 **`docs/` 目录**发布（Pages 只支持根目录和 `/docs` 两种）。

1. 在 GitHub 新建仓库（不要勾选 README）。
2. 推上去（见《手把手教程.md》第 3 步）。
3. 仓库 → Settings → Pages → Source 选 **Deploy from a branch** →
   Branch 选 `main`，目录选 **`/docs`** → Save。
4. 等 1～2 分钟，访问 `https://<你的用户名>.github.io/<仓库名>/`。

## 快捷键

| 按键 | 作用 |
|---|---|
| `Ctrl` + `K` 或 `/` | 打开全局搜索 |
| `↑` `↓` `Enter` | 搜索结果里移动 / 打开 |
| `Esc` | 关闭面板 |

## 交互点（演示时按这个顺序讲）

1. **搜索**：`Ctrl+K` 输入「Huffman」，秒出页面 + 命中片段。
2. **知识图谱**：拖动节点重排，点节点跳转，悬停看两页关系。
3. **自测卡片**：点卡片翻答案，标「我会了」，右上角计分。
4. **暗色模式**：右上角月亮，全站跟随。
5. **代码块**：右上角「复制」，答辩现场能直接贴。
