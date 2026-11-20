/* School IT Toolkit 文件站互動：閱讀進度、側欄目錄＋捲動定位、程式碼終端機框與複製、
   表格包覆、狀態燈號上色、標題錨點、浮動連結、浮現動畫。無相依套件，失敗不影響閱讀。 */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const doc = $(".doc");
  if (!doc) return;
  document.documentElement.classList.add("js");

  /* 閱讀進度條＋浮動連結「回到頂端」顯示時機 */
  const bar = document.createElement("div");
  bar.id = "progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);
  const dock = $(".dock");
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${max > 0 ? Math.min(1, scrollY / max) : 0})`;
    if (dock) dock.classList.toggle("scrolled", scrollY > innerHeight * 0.6);
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* 程式碼區塊 → 終端機視窗＋複製按鈕 */
  $$("div.highlighter-rouge, pre:not(div.highlighter-rouge pre)", doc).forEach((block) => {
    if (block.closest(".term")) return;
    const lang = ((block.className.match(/language-(\w+)/) || [])[1] || "text").replace("plaintext", "text");
    const wrap = document.createElement("div");
    wrap.className = "term";
    wrap.innerHTML = `<div class="term-bar" aria-hidden="true"><i></i><i></i><i></i><b>${lang}</b></div>`;
    block.replaceWith(wrap);
    wrap.appendChild(block);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "複製";
    btn.addEventListener("click", async () => {
      const text = ($("code", block) || block).innerText;
      try { await navigator.clipboard.writeText(text); btn.textContent = "已複製 ✓"; btn.classList.add("done"); }
      catch { btn.textContent = "請手動選取"; }
      setTimeout(() => { btn.textContent = "複製"; btn.classList.remove("done"); }, 1600);
    });
    wrap.appendChild(btn);
  });

  /* 表格可橫向捲動 */
  $$("table", doc).forEach((t) => {
    if (t.parentElement.classList.contains("table-wrap")) return;
    const w = document.createElement("div");
    w.className = "table-wrap";
    t.replaceWith(w);
    w.appendChild(t);
  });

  /* 狀態燈號：行內程式碼若是 sitk 的狀態值就上色 */
  const STATUS = {
    OK: "ok", ALL_DONE: "ok", NEXT: "info", RESUME: "info", DRY_RUN: "info", MANUAL: "warn",
    NOT_ACTIVE: "warn", UNKNOWN_ASSET: "stop", FAIL_CLOSED: "stop", OUT_OF_SCOPE: "stop", ADAPTER_ERROR: "stop",
  };
  $$(":not(pre) > code", doc).forEach((c) => {
    const k = c.textContent.trim();
    if (STATUS[k]) c.dataset.status = STATUS[k];
  });

  /* 標題錨點＋側欄目錄 */
  const heads = $$("h2[id], h3[id]", doc);
  heads.forEach((h) => {
    const a = document.createElement("a");
    a.className = "anchor";
    a.href = `#${h.id}`;
    a.textContent = "#";
    a.setAttribute("aria-label", `連到「${h.textContent}」`);
    h.appendChild(a);
  });
  const tocNav = $("#toc-nav");
  if (tocNav && heads.length) {
    tocNav.innerHTML = heads.map((h) => {
      const label = h.firstChild && h.firstChild.nodeType === 3 ? h.childNodes[0].textContent : h.textContent.replace(/#$/, "");
      return `<a class="${h.tagName === "H3" ? "lv3" : "lv2"}" href="#${h.id}">${label.trim().replace(/[<>&]/g, "")}</a>`;
    }).join("");
    const links = new Map($$("a", tocNav).map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
    let current = null;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) current = en.target.id; });
      if (!current) return;
      links.forEach((a) => a.classList.remove("on"));
      const on = links.get(current);
      if (on) { on.classList.add("on"); on.scrollIntoView({ block: "nearest" }); }
    }, { rootMargin: "-80px 0px -70% 0px" });
    heads.forEach((h) => io.observe(h));
  } else if (tocNav) {
    const aside = tocNav.closest(".toc");
    if (aside) aside.remove();
    const layout = $(".layout");
    if (layout) layout.style.gridTemplateColumns = "minmax(0, 1fr)";
  }

  /* 浮現動畫 */
  if (!reduce && "IntersectionObserver" in window) {
    const els = $$(".doc > h2, .doc > blockquote, .term, .table-wrap, .doc > p > img", doc);
    els.forEach((e) => e.classList.add("reveal"));
    const io2 = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add("in"); io2.unobserve(en.target); }
    }), { rootMargin: "0px 0px -6% 0px" });
    els.forEach((e) => io2.observe(e));
  }
})();
