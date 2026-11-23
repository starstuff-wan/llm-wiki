/* LLM Wiki · 交互脚本（零依赖） */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var isMac = /Mac|iPhone|iPad/.test(navigator.platform);

  /* ───────── 主题 ───────── */
  function applyTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('llmwiki-theme', t); } catch (e) {}
    var b = $('#themeBtn');
    if (b) b.textContent = t === 'dark' ? '☀️' : '🌙';
  }

  var savedTheme = null, urlTheme = null;
  try { urlTheme = new URLSearchParams(location.search).get('theme'); } catch (e) {}
  try { savedTheme = localStorage.getItem('llmwiki-theme'); } catch (e) {}
  applyTheme(urlTheme || savedTheme ||
    (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  var themeBtn = $('#themeBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
    });
  }

  /* ───────── 移动端侧栏 ───────── */
  var sidebar = $('#sidebar'), scrim = $('#scrim'), menuBtn = $('#menuBtn');
  function closeNav() {
    if (sidebar) sidebar.classList.remove('open');
    if (scrim) scrim.classList.remove('on');
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      var open = sidebar.classList.toggle('open');
      if (scrim) scrim.classList.toggle('on', open);
    });
  }
  if (scrim) scrim.addEventListener('click', closeNav);
  $$('.navlink').forEach(function (a) { a.addEventListener('click', closeNav); });

  /* ───────── 阅读进度 ───────── */
  var bar = $('#progressBar');
  function onScroll() {
    if (!bar) return;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (h > 0 ? Math.min(100, (window.scrollY / h) * 100) : 0) + '%';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ───────── 目录高亮 ───────── */
  var tocLinks = $$('.toc a');
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var heads = Object.keys(map).map(function (id) {
      return document.getElementById(id);
    }).filter(Boolean);
    var current = null;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          if (current) current.classList.remove('on');
          current = map[e.target.id];
          if (current) current.classList.add('on');
        }
      });
    }, { rootMargin: '-72px 0px -70% 0px' });
    heads.forEach(function (h) { io.observe(h); });
  }

  /* ───────── 代码复制 ───────── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.copy') : null;
    if (!btn) return;
    var pre = btn.closest('.codeblock').querySelector('code');
    var text = pre ? pre.textContent : '';
    var done = function () {
      btn.textContent = '已复制 ✓';
      setTimeout(function () { btn.textContent = '复制'; }, 1600);
    };
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); done(); } catch (err) {}
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(fallback);
    } else {
      fallback();
    }
  });

  /* ───────── 搜索面板 ───────── */
  var palette = $('#palette'), input = $('#searchInput'), resultsEl = $('#searchResults');
  var index = null, results = [], sel = -1, loading = false;

  function openPalette() {
    if (!palette) return;
    palette.hidden = false;
    document.body.style.overflow = 'hidden';
    input.value = '';
    input.focus();
    render('');
    if (!index && !loading) {
      loading = true;
      fetch('search-index.json')
        .then(function (r) { return r.json(); })
        .then(function (d) { index = d; loading = false; render(input.value); })
        .catch(function () { index = []; loading = false; render(input.value); });
    }
  }

  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    document.body.style.overflow = '';
    sel = -1;
  }

  function score(item, q) {
    var t = item.t.toLowerCase(), x = (item.x || '').toLowerCase(), s = 0;
    if (t.indexOf(q) >= 0) s += 10;
    if (t === q) s += 20;
    var i = x.indexOf(q);
    if (i >= 0) { s += 3 + Math.max(0, 4 - i / 400); }
    return s;
  }

  function snippet(item, q) {
    var x = item.x || '';
    var i = x.toLowerCase().indexOf(q);
    if (i < 0) return x.slice(0, 56) + (x.length > 56 ? '…' : '');
    var start = Math.max(0, i - 18);
    return (start > 0 ? '…' : '') + x.slice(start, start + 70).trim() + '…';
  }

  function render(q) {
    if (!resultsEl) return;
    q = (q || '').trim().toLowerCase();
    if (!index) {
      resultsEl.innerHTML = '<div class="pempty">正在载入索引…</div>';
      return;
    }
    if (!q) {
      results = index.slice(0, 9);
    } else {
      results = index
        .map(function (it) { return { it: it, s: score(it, q) }; })
        .filter(function (o) { return o.s > 0; })
        .sort(function (a, b) { return b.s - a.s; })
        .slice(0, 9)
        .map(function (o) { return o.it; });
    }
    if (!results.length) {
      resultsEl.innerHTML = '<div class="pempty">没有匹配「' + q.replace(/[<>&]/g, '') + '」的页面</div>';
      sel = -1;
      return;
    }
    resultsEl.innerHTML = results.map(function (it, k) {
      return '<div class="pitem' + (k === sel ? ' sel' : '') + '" data-k="' + k + '" data-u="' + it.u + '">' +
        '<span class="pg2">' + (it.g || '') + '</span>' +
        '<b>' + it.t + '</b>' +
        '<small>' + (q ? snippet(it, q) : (it.x || '').slice(0, 56) + '…') + '</small>' +
        '</div>';
    }).join('');
  }

  function highlight() {
    $$('.pitem', resultsEl).forEach(function (el, k) {
      el.classList.toggle('sel', k === sel);
      if (k === sel) el.scrollIntoView({ block: 'nearest' });
    });
  }

  if (input) {
    input.addEventListener('input', function () { sel = 0; render(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(sel + 1, results.length - 1); highlight(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(sel - 1, 0); highlight(); }
      else if (e.key === 'Enter' && results[sel]) { location.href = results[sel].u; }
      else if (e.key === 'Escape') { closePalette(); }
    });
  }
  if (resultsEl) {
    resultsEl.addEventListener('click', function (e) {
      var it = e.target.closest('.pitem');
      if (it) location.href = it.getAttribute('data-u');
    });
  }
  if (palette) palette.addEventListener('click', function (e) { if (e.target === palette) closePalette(); });
  var trigger = $('#searchTrigger');
  if (trigger) trigger.addEventListener('click', openPalette);

  document.addEventListener('keydown', function (e) {
    var k = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && k === 'k') { e.preventDefault(); openPalette(); return; }
    if (k === '/' && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); openPalette(); }
    if (e.key === 'Escape') { closePalette(); closeNav(); }
  });
  $$('kbd').forEach(function (k) {
    if (k.textContent === 'Ctrl' && isMac) k.textContent = '⌘';
  });

  /* ───────── 自测卡片 ───────── */
  (function () {
    var cards = $$('.qgrid .qcard');
    if (!cards.length) return;
    var doneEl = $('#done'), knownEl = $('#known');
    var doneSet = {}, knownSet = {};
    var doneCount = 0, knownCount = 0;
    function sync() {
      if (doneEl) doneEl.textContent = doneCount;
      if (knownEl) knownEl.textContent = knownCount;
    }
    cards.forEach(function (c) {
      var id = c.dataset.i;
      c.addEventListener('click', function (e) {
        if (e.target.closest('.mark')) return;
        c.classList.toggle('open');
        if (c.classList.contains('open') && !doneSet[id]) { doneSet[id] = 1; doneCount++; sync(); }
      });
      c.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); c.click(); }
      });
      var mark = c.querySelector('.mark');
      if (mark) {
        mark.addEventListener('click', function (e) {
          e.stopPropagation();
          c.classList.toggle('known');
          if (c.classList.contains('known')) {
            if (!knownSet[id]) { knownSet[id] = 1; knownCount++; }
            c.classList.add('open');
            if (!doneSet[id]) { doneSet[id] = 1; doneCount++; }
          } else if (knownSet[id]) {
            delete knownSet[id]; knownCount--;
          }
          sync();
        });
      }
    });
    var reset = $('#resetQuiz');
    if (reset) {
      reset.addEventListener('click', function () {
        cards.forEach(function (c) { c.classList.remove('open', 'known'); });
        doneSet = {}; knownSet = {}; doneCount = 0; knownCount = 0; sync();
      });
    }
  })();

  /* ───────── 知识图谱 ───────── */
  (function () {
    var holder = document.getElementById('graph-data');
    var svg = document.getElementById('graphSvg');
    if (!holder || !svg) return;

    var data = JSON.parse(holder.textContent);
    var NS = 'http://www.w3.org/2000/svg';
    var COLORS = {
      '起步': '#6366f1', '核心原理': '#0ea5e9', '三种算法': '#14b8a6',
      '质量评估': '#f59e0b', '工程实践': '#8b5cf6', '答辩准备': '#ef4444', '互动': '#64748b'
    };
    var wrap = svg.parentElement;
    var W = wrap.clientWidth || 800, H = wrap.clientHeight || 560;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    var nodes = data.nodes.map(function (n, i) {
      var a = (i / data.nodes.length) * Math.PI * 2;
      return {
        id: n.id, t: n.t, g: n.g, w: n.w || 4,
        x: W / 2 + Math.cos(a) * (W / 4),
        y: H / 2 + Math.sin(a) * (H / 4),
        vx: 0, vy: 0, r: 12 + (n.w || 4) * 2.6, fixed: false
      };
    });
    var byId = {};
    nodes.forEach(function (n) { byId[n.id] = n; });
    var links = data.edges
      .filter(function (e) { return byId[e.s] && byId[e.t]; })
      .map(function (e) { return { s: byId[e.s], t: byId[e.t], l: e.l || '' }; });

    var gEdges = document.createElementNS(NS, 'g');
    var gLabels = document.createElementNS(NS, 'g');
    var gNodes = document.createElementNS(NS, 'g');
    svg.appendChild(gEdges);
    svg.appendChild(gLabels);
    svg.appendChild(gNodes);

    links.forEach(function (l) {
      l.line = document.createElementNS(NS, 'line');
      l.line.setAttribute('class', 'gedge');
      gEdges.appendChild(l.line);
      l.text = document.createElementNS(NS, 'text');
      l.text.setAttribute('class', 'gedge-label');
      l.text.textContent = l.l;
      gLabels.appendChild(l.text);
    });

    function truncate(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }

    function toSvg(cx, cy) {
      var r = svg.getBoundingClientRect();
      var sc = Math.min(r.width / W, r.height / H);
      var ox = (r.width - W * sc) / 2, oy = (r.height - H * sc) / 2;
      return { x: (cx - r.left - ox) / sc, y: (cy - r.top - oy) / sc };
    }

    nodes.forEach(function (n, idx) {
      n.grp = document.createElementNS(NS, 'g');
      n.grp.setAttribute('class', 'gnode');
      n.circle = document.createElementNS(NS, 'circle');
      n.circle.setAttribute('r', n.r);
      n.circle.setAttribute('fill', COLORS[n.g] || '#64748b');
      n.circle.setAttribute('fill-opacity', '0.9');
      n.circle.setAttribute('stroke', 'rgba(255,255,255,.85)');
      n.circle.setAttribute('stroke-width', '1.5');
      n.label = document.createElementNS(NS, 'text');
      n.label.textContent = truncate(n.t, 6);
      n.above = idx % 2 === 1;
      n.grp.appendChild(n.circle);
      n.grp.appendChild(n.label);
      n.grp.style.cursor = 'pointer';
      n.grp.addEventListener('click', function () { location.href = n.id + '.html'; });
      n.grp.addEventListener('pointerdown', function (ev) {
        ev.preventDefault();
        n.fixed = true;
        n.grp.setPointerCapture(ev.pointerId);
        function move(e2) {
          var pt = toSvg(e2.clientX, e2.clientY);
          n.x = pt.x; n.y = pt.y; n.vx = n.vy = 0;
          alpha = Math.max(alpha, 0.28);
          kick();
        }
        function up() {
          n.fixed = false;
          n.grp.removeEventListener('pointermove', move);
          n.grp.removeEventListener('pointerup', up);
          n.grp.removeEventListener('pointercancel', up);
        }
        n.grp.addEventListener('pointermove', move);
        n.grp.addEventListener('pointerup', up);
        n.grp.addEventListener('pointercancel', up);
      });
      n.grp.addEventListener('pointerenter', function () {
        links.forEach(function (l) { if (l.s === n || l.t === n) l.text.style.opacity = '1'; });
      });
      n.grp.addEventListener('pointerleave', function () {
        links.forEach(function (l) { l.text.style.opacity = '0'; });
      });
      gNodes.appendChild(n.grp);
    });

    var alpha = 1, raf = null;

    function kick() {
      if (raf) return;
      raf = requestAnimationFrame(tick);
    }

    function tick() {
      raf = null;
      alpha *= 0.985;
      var i, j, a, b;

      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j];
          var dx = b.x - a.x, dy = b.y - a.y;
          var d2 = dx * dx + dy * dy;
          if (d2 < 1) { d2 = 1; dx = Math.random() - 0.5; dy = Math.random() - 0.5; }
          var d = Math.sqrt(d2);
          var f = Math.min(220, 24000 / d2) * alpha;
          var ux = dx / d, uy = dy / d;
          a.vx -= ux * f; a.vy -= uy * f;
          b.vx += ux * f; b.vy += uy * f;
        }
      }

      links.forEach(function (l) {
        var dx = l.t.x - l.s.x, dy = l.t.y - l.s.y;
        var d = Math.sqrt(dx * dx + dy * dy) || 1;
        var f = (d - 150) * 0.008 * alpha;
        var ux = dx / d, uy = dy / d;
        l.s.vx += ux * f; l.s.vy += uy * f;
        l.t.vx -= ux * f; l.t.vy -= uy * f;
      });

      nodes.forEach(function (n) {
        n.vx += (W / 2 - n.x) * 0.0011 * alpha;
        n.vy += (H / 2 - n.y) * 0.0011 * alpha;
        if (n.fixed) { n.vx = n.vy = 0; return; }
        n.vx *= 0.86; n.vy *= 0.86;
        n.x += n.vx; n.y += n.vy;
      });

      // 拆开重叠的节点，给标签留出空间
      for (i = 0; i < nodes.length; i++) {
        for (j = i + 1; j < nodes.length; j++) {
          a = nodes[i]; b = nodes[j];
          var ox = b.x - a.x, oy = b.y - a.y;
          var od = Math.sqrt(ox * ox + oy * oy) || 1;
          var minD = a.r + b.r + 58;
          if (od < minD) {
            var push = (minD - od) / 2;
            a.x -= (ox / od) * push; a.y -= (oy / od) * push;
            b.x += (ox / od) * push; b.y += (oy / od) * push;
          }
        }
      }

      nodes.forEach(function (n) {
        var pad = n.r + 34;
        n.x = Math.max(pad, Math.min(W - pad, n.x));
        n.y = Math.max(pad, Math.min(H - pad, n.y));
      });

      draw();
      if (alpha > 0.02) raf = requestAnimationFrame(tick);
    }

    function draw() {
      links.forEach(function (l) {
        l.line.setAttribute('x1', l.s.x); l.line.setAttribute('y1', l.s.y);
        l.line.setAttribute('x2', l.t.x); l.line.setAttribute('y2', l.t.y);
        l.text.setAttribute('x', (l.s.x + l.t.x) / 2);
        l.text.setAttribute('y', (l.s.y + l.t.y) / 2 - 4);
      });
      nodes.forEach(function (n) {
        n.circle.setAttribute('cx', n.x);
        n.circle.setAttribute('cy', n.y);
        // 标签沿半径向外排，避免压在连线和别的节点上
        var vx = n.x - W / 2, vy = n.y - H / 2;
        var vl = Math.sqrt(vx * vx + vy * vy) || 1;
        var ux = vx / vl, uy = vy / vl;
        if (ux > 0.45) {
          n.label.style.textAnchor = 'start';
          n.label.setAttribute('x', n.x + n.r + 6);
          n.label.setAttribute('y', n.y + 4);
        } else if (ux < -0.45) {
          n.label.style.textAnchor = 'end';
          n.label.setAttribute('x', n.x - n.r - 6);
          n.label.setAttribute('y', n.y + 4);
        } else {
          n.label.style.textAnchor = 'middle';
          n.label.setAttribute('x', n.x);
          n.label.setAttribute('y', uy < 0 ? n.y - n.r - 8 : n.y + n.r + 15);
        }
      });
    }

    draw();
    kick();

    var legend = document.getElementById('glegend');
    if (legend) {
      var groups = [];
      data.nodes.forEach(function (n) { if (groups.indexOf(n.g) < 0) groups.push(n.g); });
      legend.innerHTML = groups.map(function (g) {
        return '<span><i style="background:' + (COLORS[g] || '#64748b') + '"></i>' + g + '</span>';
      }).join('');
    }
  })();
})();
