/* School IT Toolkit 文件站互動（Holo-Lab 版）
   英雄區網路星球動畫、章節編號與配色、目錄卡片牆、防護層圖卡、程式碼終端機框與複製、
   狀態燈號、聚光邊框、依章節變色的氛圍、側欄目錄＋捲動定位、浮動連結。無相依套件，失敗不影響閱讀。 */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;
  const doc = $(".doc");
  if (!doc) return;
  root.classList.add("js");
  const HUES = [188, 214, 258, 292, 330, 28, 84, 160];
  const pad = (n) => String(n).padStart(2, "0");

  /* ── 閱讀進度條＋浮動連結「回到頂端」 ── */
  const bar = el("div");
  bar.id = "progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);
  const dock = $(".dock");
  const tocCard = $(".toc-card");
  const onScroll = () => {
    const max = root.scrollHeight - innerHeight;
    const p = max > 0 ? Math.min(1, scrollY / max) : 0;
    bar.style.transform = `scaleX(${p})`;
    if (tocCard) tocCard.style.setProperty("--p", p.toFixed(4));
    if (dock) dock.classList.toggle("scrolled", scrollY > innerHeight * 0.6);
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ── 移除與版型重複的內容（頂部導覽列、作者資訊引言） ── */
  $$(".doc > p").slice(0, 3).forEach((p) => { if (/回到首頁/.test(p.textContent) && p.querySelector("a")) p.remove(); });
  $$(".doc > blockquote").slice(0, 2).forEach((q) => { if (/^\s*作者：/.test(q.textContent)) q.remove(); });

  /* ── 首張大圖 → 全像框 ── */
  const firstImg = $(".doc > p > img");
  if (firstImg && firstImg.parentElement.children.length === 1) {
    const holo = el("figure", "holo");
    holo.innerHTML = '<i class="hc tl"></i><i class="hc tr"></i><i class="hc bl"></i><i class="hc br"></i><span class="holo-scan" aria-hidden="true"></span>';
    firstImg.parentElement.replaceWith(holo);
    holo.prepend(firstImg);
  }

  /* ── 程式碼區塊：方框圖 → 防護層圖卡；其餘 → 終端機視窗＋複製 ── */
  $$("div.highlighter-rouge, pre:not(div.highlighter-rouge pre)", doc).forEach((block) => {
    if (block.closest(".term")) return;
    const raw = ($("code", block) || block).textContent;
    const rows = [...raw.matchAll(/│\s*(\d+)\.\s*(\S+?)\s*│\s*(.+?)\s*│/g)];
    if (rows.length >= 3 && /[┌└]/.test(raw)) {
      const stack = el("div", "stack spot");
      stack.setAttribute("role", "list");
      rows.forEach(([, n, name, desc], i) => {
        const item = el("div", "stack-layer");
        item.setAttribute("role", "listitem");
        item.style.setProperty("--h", HUES[(i * 2) % HUES.length]);
        item.append(el("b", "stack-n", pad(n)), el("strong", "", name), el("span", "", desc));
        stack.appendChild(item);
      });
      block.replaceWith(stack);
      return;
    }
    const lang = ((block.className.match(/language-(\w+)/) || [])[1] || "text").replace("plaintext", "text");
    const wrap = el("div", "term spot");
    wrap.innerHTML = `<div class="term-bar" aria-hidden="true"><i></i><i></i><i></i><b>${lang === "text" ? "output" : lang}</b></div>`;
    block.replaceWith(wrap);
    wrap.appendChild(block);
    const btn = el("button", "copy", "複製");
    btn.type = "button";
    btn.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(raw.replace(/\n$/, "")); btn.textContent = "已複製 ✓"; btn.classList.add("done"); }
      catch { btn.textContent = "請手動選取"; }
      setTimeout(() => { btn.textContent = "複製"; btn.classList.remove("done"); }, 1600);
    });
    wrap.appendChild(btn);
  });

  /* ── 表格可橫向捲動 ── */
  $$("table", doc).forEach((t) => {
    if (t.parentElement.classList.contains("table-wrap")) return;
    const w = el("div", "table-wrap spot");
    t.replaceWith(w);
    w.appendChild(t);
  });
  $$(".doc blockquote").forEach((q) => q.classList.add("spot"));

  /* ── 狀態燈號 ── */
  const STATUS = {
    OK: "ok", ALL_DONE: "ok", NEXT: "info", RESUME: "info", DRY_RUN: "info", MANUAL: "warn",
    NOT_ACTIVE: "warn", UNKNOWN_ASSET: "stop", FAIL_CLOSED: "stop", OUT_OF_SCOPE: "stop", ADAPTER_ERROR: "stop",
  };
  $$(":not(pre) > code", doc).forEach((c) => { const k = c.textContent.trim(); if (STATUS[k]) c.dataset.status = STATUS[k]; });

  /* ── 章節化：每個 h2 起一個 section，帶編號與專屬色相 ── */
  const heads2 = $$(".doc > h2");
  let chapterNo = 0;
  heads2.forEach((h, idx) => {
    const text = h.textContent.trim();
    h.dataset.label = text;
    const m = text.match(/^(\d+)\.\s*(.+)$/);
    const isIndex = /^目錄$/.test(text);
    const n = m ? +m[1] : null;
    if (n) chapterNo = n;
    const hue = n ? HUES[(n - 1) % HUES.length] : isIndex ? 188 : HUES[(chapterNo + idx) % HUES.length];
    const sec = el("section", `chapter${n ? "" : " chapter-plain"}`);
    sec.style.setProperty("--h", hue);
    sec.dataset.h = hue;
    h.before(sec);
    let node = h;
    while (node && !(node !== h && node.tagName === "H2")) { const next = node.nextElementSibling; sec.appendChild(node); node = next; }
    const title = m ? m[2] : text;
    h.textContent = "";
    h.classList.add("ch");
    if (n) h.appendChild(el("span", "ch-num", pad(n))).setAttribute("aria-hidden", "true");
    /* 章節標題的「1. 」只留給螢幕報讀器，視覺用大編號呈現 */
    const tt = el("span", "ch-title", title);
    if (n) tt.prepend(el("span", "sr", `${n}. `));
    h.append(el("span", "ch-kicker", n ? `CHAPTER ${pad(n)}` : isIndex ? "INDEX · 本文章節" : "APPENDIX"), tt);
  });

  /* ── 文內「目錄」清單 → 章節卡片牆 ── */
  const indexSec = $$(".chapter-plain").find((s) => /^目錄$/.test(s.querySelector("h2").dataset.label));
  if (indexSec) {
    const list = indexSec.querySelector("ol, ul");
    if (list) {
      const grid = el("nav", "ch-grid");
      grid.setAttribute("aria-label", "本文章節");
      $$(":scope > li", list).forEach((li, i) => {
        const a = li.querySelector("a");
        if (!a) return;
        const card = el("a", "ch-card spot");
        card.href = a.getAttribute("href");
        card.style.setProperty("--h", HUES[i % HUES.length]);
        card.append(el("b", "", pad(i + 1)), el("span", "", a.textContent.replace(/^\d+\.\s*/, "")), el("i", "", "→"));
        grid.appendChild(card);
      });
      list.replaceWith(grid);
    }
  }

  /* ── 標題錨點 ── */
  const heads = $$("h2[id], h3[id]", doc);
  heads.forEach((h) => {
    const a = el("a", "anchor", "#");
    a.href = `#${h.id}`;
    a.setAttribute("aria-label", "複製本段連結");
    h.appendChild(a);
  });

  /* ── 側欄目錄＋捲動定位＋依章節換氛圍色 ── */
  const tocNav = $("#toc-nav");
  if (tocNav && heads.length) {
    heads.forEach((h) => {
      const isH3 = h.tagName === "H3";
      const a = el("a", isH3 ? "lv3" : "lv2");
      a.href = `#${h.id}`;
      const sec = h.closest(".chapter");
      if (sec) a.style.setProperty("--h", sec.dataset.h);
      const num = h.querySelector(".ch-num");
      if (num) a.appendChild(el("b", "", num.textContent));
      a.append(isH3 ? (h.firstChild?.textContent || h.textContent).replace(/#$/, "").trim()
        : (h.querySelector(".ch-title")?.textContent || h.dataset.label || "").replace(/^\d+\.\s*/, "").trim());
      tocNav.appendChild(a);
    });
    const links = new Map($$("a", tocNav).map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
    let current = null, spyRaf = 0;
    const spy = () => {
      spyRaf = 0;
      let id = heads[0].id;
      for (const h of heads) { if (h.getBoundingClientRect().top < 140) id = h.id; else break; }
      if (id === current) return;
      current = id;
      links.forEach((a) => a.classList.remove("on"));
      const on = links.get(id);
      if (on) { on.classList.add("on"); const r = on.offsetTop - tocNav.clientHeight / 2; tocNav.scrollTo({ top: Math.max(0, r), behavior: reduce ? "auto" : "smooth" }); }
      const sec = document.getElementById(id)?.closest(".chapter");
      if (sec) root.style.setProperty("--page-h", sec.dataset.h);
    };
    addEventListener("scroll", () => { if (!spyRaf) spyRaf = requestAnimationFrame(spy); }, { passive: true });
    spy();
  } else if (tocNav) {
    tocNav.closest(".toc")?.remove();
    const layout = $(".layout");
    if (layout) layout.classList.add("no-toc");
  }

  /* ── 英雄區數據列 ── */
  const stats = $(".hero-stats");
  if (stats) {
    const data = [
      [$$(".ch-num").length, "個章節"],
      [$$(".term").length, "段指令範例"],
      [+(stats.dataset.min || 0), "分鐘讀完"],
      [0, "次 AI 擅自變更"],
    ].filter(([v], i) => v > 0 || i === 3);
    stats.innerHTML = data.map(([v, t]) => `<div><b data-to="${v}">${reduce ? v : 0}</b><span>${t}</span></div>`).join("");
    if (!reduce) {
      const t0 = performance.now();
      const tick = (t) => {
        const k = Math.min(1, (t - t0) / 1400), e = 1 - Math.pow(1 - k, 3);
        $$("b[data-to]", stats).forEach((b) => { b.textContent = Math.round(+b.dataset.to * e); });
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }

  /* ── 聚光邊框＋游標光暈 ── */
  if (matchMedia("(hover: hover)").matches) {
    const glow = el("div");
    glow.id = "cursor-glow";
    glow.setAttribute("aria-hidden", "true");
    document.body.appendChild(glow);
    let raf = 0, mx = 0, my = 0, tgt = null;
    addEventListener("pointermove", (e) => {
      mx = e.clientX; my = e.clientY; tgt = e.target.closest ? e.target.closest(".spot") : null;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        glow.style.transform = `translate(${mx}px, ${my}px)`;
        if (tgt) { const r = tgt.getBoundingClientRect(); tgt.style.setProperty("--mx", `${mx - r.left}px`); tgt.style.setProperty("--my", `${my - r.top}px`); }
      });
    }, { passive: true });
  }

  /* ── 浮現動畫 ── */
  if (!reduce && "IntersectionObserver" in window) {
    const els = $$(".chapter > h2, .doc blockquote, .term, .table-wrap, .holo, .stack, .ch-card", doc);
    els.forEach((e) => e.classList.add("reveal"));
    $$(".ch-card").forEach((c, i) => c.style.setProperty("--d", `${(i % 4) * 60}ms`));
    const io2 = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add("in"); io2.unobserve(en.target); }
    }), { rootMargin: "0px 0px -6% 0px" });
    els.forEach((e) => io2.observe(e));
  }

  /* ── 英雄區：校園網路星球（Canvas 2D） ── */
  const cv = $(".hero-art");
  if (cv && cv.getContext) heroArt(cv);

  function heroArt(canvas) {
    const g = canvas.getContext("2d");
    const hero = canvas.parentElement;
    const DPR = Math.min(devicePixelRatio || 1, 2);
    const N = innerWidth < 720 ? 150 : 240;
    const pts = [];
    const ga = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = ga * i;
      pts.push([Math.cos(th) * r, y, Math.sin(th) * r]);
    }
    // 每點連最近 3 點
    const edges = [], seen = new Set();
    pts.forEach((a, i) => {
      pts.map((b, j) => [j, (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2]).filter(([j]) => j !== i)
        .sort((x, y) => x[1] - y[1]).slice(0, 3).forEach(([j]) => { const k = i < j ? `${i}-${j}` : `${j}-${i}`; if (!seen.has(k)) { seen.add(k); edges.push([i, j]); } });
    });
    const hubs = Array.from({ length: 14 }, (_, k) => Math.floor((k * 0.618034 % 1) * N));
    const COLORS = ["34,211,238", "129,140,248", "244,114,182", "163,230,53", "251,191,36"];
    const packets = Array.from({ length: N > 200 ? 46 : 28 }, () => ({ e: (Math.random() * edges.length) | 0, t: Math.random(), v: 0.004 + Math.random() * 0.01, c: COLORS[(Math.random() * COLORS.length) | 0] }));
    let W = 0, H = 0, cx = 0, cy = 0, R = 0, alpha = 1;
    const resize = () => {
      W = hero.clientWidth; H = hero.clientHeight;
      canvas.width = W * DPR; canvas.height = H * DPR;
      canvas.style.width = `${W}px`; canvas.style.height = `${H}px`;
      g.setTransform(DPR, 0, 0, DPR, 0, 0);
      const wide = W > 1080;
      cx = wide ? W * 0.5 + Math.min(W, 1240) * 0.29 : W * 0.82;
      cy = wide ? H * 0.47 : H * 0.2;
      R = wide ? Math.min(H * 0.4, 300) : Math.min(W * 0.46, 220);
      alpha = wide ? 1 : 0.35;
    };
    new ResizeObserver(resize).observe(hero);
    resize();
    let tiltX = 0.35, tiltY = 0, tx = 0.35, ty = 0;
    hero.addEventListener("pointermove", (e) => { const r = hero.getBoundingClientRect(); ty = ((e.clientX - r.left) / r.width - 0.5) * 0.8; tx = 0.35 + ((e.clientY - r.top) / r.height - 0.5) * 0.5; }, { passive: true });
    const proj = new Array(N);
    let visible = true;
    new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(hero);
    const ring = (rr, tilt, rot, color, dash) => {
      g.save(); g.translate(cx, cy); g.rotate(rot); g.scale(1, Math.abs(Math.sin(tilt)) * 0.9 + 0.08);
      g.beginPath(); g.setLineDash(dash || []); g.arc(0, 0, rr, 0, Math.PI * 2); g.strokeStyle = color; g.lineWidth = 1; g.stroke(); g.restore();
    };
    const draw = (t) => {
      tiltX += (tx - tiltX) * 0.04; tiltY += (ty - tiltY) * 0.04;
      const ay = t * 0.00012 + tiltY, ax = tiltX;
      const sy = Math.sin(ay), cyy = Math.cos(ay), sx = Math.sin(ax), cxx = Math.cos(ax);
      g.clearRect(0, 0, W, H);
      g.globalAlpha = alpha;
      // 光暈
      const halo = g.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.6);
      halo.addColorStop(0, "rgba(99,102,241,0.20)"); halo.addColorStop(0.5, "rgba(34,211,238,0.06)"); halo.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = halo; g.fillRect(cx - R * 1.7, cy - R * 1.7, R * 3.4, R * 3.4);
      // 軌道環
      ring(R * 1.28, ax + 0.3, -0.35 + t * 0.00003, "rgba(34,211,238,0.22)", [2, 6]);
      ring(R * 1.48, ax - 0.5, 0.5 - t * 0.00002, "rgba(244,114,182,0.16)");
      ring(R * 1.06, ax + 1.2, 0.15, "rgba(129,140,248,0.18)", [1, 4]);
      for (let i = 0; i < N; i++) {
        const [x, y, z] = pts[i];
        const x1 = x * cyy + z * sy, z1 = -x * sy + z * cyy;
        const y2 = y * cxx - z1 * sx, z2 = y * sx + z1 * cxx;
        const s = 2.6 / (2.6 - z2);
        proj[i] = [cx + x1 * R * s, cy + y2 * R * s, z2];
      }
      g.lineWidth = 0.7;
      for (const [i, j] of edges) {
        const a = proj[i], b = proj[j], d = (a[2] + b[2]) / 2;
        if (d < -0.65) continue;
        g.strokeStyle = `rgba(125,170,255,${0.05 + (d + 1) * 0.13})`;
        g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke();
      }
      for (let i = 0; i < N; i++) {
        const [px, py, z] = proj[i];
        const r = 0.6 + (z + 1) * 0.9;
        g.fillStyle = `rgba(200,225,255,${0.18 + (z + 1) * 0.35})`;
        g.fillRect(px - r / 2, py - r / 2, r, r);
      }
      hubs.forEach((h, k) => {
        const [px, py, z] = proj[h];
        if (z < -0.2) return;
        const c = COLORS[k % COLORS.length], pulse = (t * 0.001 + k * 0.37) % 1;
        g.strokeStyle = `rgba(${c},${(1 - pulse) * 0.7 * (z + 1) / 2})`;
        g.beginPath(); g.arc(px, py, 3 + pulse * 14, 0, Math.PI * 2); g.stroke();
        g.fillStyle = `rgba(${c},${0.5 + z * 0.5})`;
        g.beginPath(); g.arc(px, py, 2.6, 0, Math.PI * 2); g.fill();
      });
      for (const p of packets) {
        if (!reduce) p.t += p.v;
        if (p.t > 1) { p.t = 0; p.e = (Math.random() * edges.length) | 0; }
        const [i, j] = edges[p.e], a = proj[i], b = proj[j];
        const z = a[2] + (b[2] - a[2]) * p.t;
        if (z < -0.3) continue;
        const x = a[0] + (b[0] - a[0]) * p.t, y = a[1] + (b[1] - a[1]) * p.t;
        g.fillStyle = `rgba(${p.c},0.18)`; g.beginPath(); g.arc(x, y, 6, 0, Math.PI * 2); g.fill();
        g.fillStyle = `rgba(${p.c},0.95)`; g.beginPath(); g.arc(x, y, 1.8, 0, Math.PI * 2); g.fill();
      }
      g.globalAlpha = 1;
    };
    if (reduce) { draw(0); return; }
    const loop = (t) => { requestAnimationFrame(loop); if (visible && !document.hidden) draw(t); };
    requestAnimationFrame(loop);
  }
})();
