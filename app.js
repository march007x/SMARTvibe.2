/* SmartVibe — สคริปต์ของหน้าเว็บ
   ไม่มีไลบรารีภายนอก ทำงานได้แม้เปิดไฟล์จากเครื่องโดยไม่มีเน็ต */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("js");   // เปิดใช้แอนิเมชัน fade-in เฉพาะเมื่อ JS ทำงานจริง

  /* ---------- 1. ธีมสว่าง/มืด ---------- */
  var THEME_KEY = "smartvibe-theme";
  var theme = "";                       // "" = ตามระบบ, "light", "dark"

  try {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") theme = saved;
  } catch (e) { /* โหมดส่วนตัว หรือเบราว์เซอร์ปิด storage — ไม่เป็นไร */ }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function applyTheme() {
    root.setAttribute("data-theme", theme);
    var dark = theme === "dark" || (theme === "" && systemPrefersDark());
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#100f0d" : "#fbfaf8");
  }

  applyTheme();

  var btnTheme = document.getElementById("btn-theme");
  if (btnTheme) {
    btnTheme.addEventListener("click", function () {
      var dark = theme === "dark" || (theme === "" && systemPrefersDark());
      theme = dark ? "light" : "dark";
      applyTheme();
      try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    });
  }

  /* ---------- 2. Overlay (เมนู + เนื้อล้วน) ---------- */
  var openOverlay = null;
  var lastFocus = null;

  function open(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (openOverlay && openOverlay !== el) close();
    lastFocus = document.activeElement;
    el.classList.add("open");
    openOverlay = el;
    document.body.style.overflow = "hidden";
    el.scrollTop = 0;
    var first = el.querySelector("button, a");
    if (first) first.focus();
  }

  function close() {
    if (!openOverlay) return;
    openOverlay.classList.remove("open");
    openOverlay = null;
    document.body.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function bindOpen(btnId, overlayId) {
    var b = document.getElementById(btnId);
    if (b) b.addEventListener("click", function () { open(overlayId); });
  }

  bindOpen("btn-menu", "menu");
  bindOpen("btn-essentials", "essentials");
  bindOpen("btn-essentials-2", "essentials");

  Array.prototype.forEach.call(document.querySelectorAll("[data-close]"), function (b) {
    b.addEventListener("click", close);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && openOverlay) close();
  });

  /* กดการ์ดหัวข้อ → ปิด overlay แล้วเลื่อนไปยังส่วนนั้น */
  Array.prototype.forEach.call(document.querySelectorAll("#menu .menu-card"), function (a) {
    a.addEventListener("click", function (e) {
      var id = a.getAttribute("href");
      if (!id || id.charAt(0) !== "#") return;
      e.preventDefault();
      close();
      var target = document.querySelector(id);
      if (!target) return;
      // รอให้ overlay ปิดก่อนค่อยเลื่อน ไม่งั้นตำแหน่งเพี้ยน
      window.setTimeout(function () {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        if (history.replaceState) history.replaceState(null, "", id);
      }, 60);
    });
  });

  /* ---------- 3. ปุ่มพิมพ์ ---------- */
  var btnPrint = document.getElementById("btn-print");
  if (btnPrint) {
    btnPrint.addEventListener("click", function () { window.print(); });
  }

  /* ---------- 4. แถบความคืบหน้าการอ่าน ---------- */
  var bar = document.getElementById("progress");
  var ticking = false;

  function updateProgress() {
    ticking = false;
    if (!bar) return;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var pct = h > 0 ? (window.pageYOffset / h) * 100 : 0;
    bar.style.width = Math.max(0, Math.min(100, pct)) + "%";
  }

  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(updateProgress); }
  }, { passive: true });

  window.addEventListener("resize", updateProgress);
  updateProgress();

  /* ---------- 5. แผนผังระบบแบบกดได้ ---------- */
  var note = document.getElementById("system-note");
  var hits = document.querySelectorAll("#fig-system .d-hit");

  function showBox(g) {
    if (!note) return;
    Array.prototype.forEach.call(hits, function (o) { o.setAttribute("aria-expanded", "false"); });
    g.setAttribute("aria-expanded", "true");
    note.innerHTML = "";
    var b = document.createElement("b");
    b.textContent = g.getAttribute("data-t") || "";
    var span = document.createElement("span");
    span.textContent = g.getAttribute("data-d") || "";
    note.appendChild(b);
    note.appendChild(span);
  }

  Array.prototype.forEach.call(hits, function (g) {
    g.addEventListener("click", function () { showBox(g); });
    g.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showBox(g); }
    });
  });

  /* ---------- 6. กราฟความไว : crosshair + tooltip ---------- */
  (function () {
    var svg = document.getElementById("chart-sens");
    var tip = document.getElementById("sens-tip");
    if (!svg || !tip) return;

    var DATA = [
      { k: "10%", fn: "1.9%",  t: "+5.4%",  sfn: "ปกติ",           st: "ปกติ" },
      { k: "20%", fn: "4.1%",  t: "+12.2%", sfn: "ยังบอกว่าปกติ",  st: "จับได้แล้ว" },
      { k: "30%", fn: "6.9%",  t: "+21.2%", sfn: "เฝ้าระวัง",       st: "อันตราย" },
      { k: "40%", fn: "10.2%", t: "+33.2%", sfn: "เฝ้าระวัง",       st: "อันตราย" },
      { k: "50%", fn: "14.3%", t: "+50.4%", sfn: "เฝ้าระวัง",       st: "อันตราย" }
    ];
    var XS = [56, 200, 343, 487, 630];       // ตำแหน่งบนแกน x ในหน่วย viewBox
    var VB_W = 800;

    var cross = document.createElementNS("http://www.w3.org/2000/svg", "line");
    cross.setAttribute("class", "d-grid");
    cross.setAttribute("y1", "26");
    cross.setAttribute("y2", "334");
    cross.setAttribute("stroke-width", "1.5");
    cross.style.opacity = "0";
    svg.insertBefore(cross, document.getElementById("sens-hit"));

    function show(i, host) {
      var d = DATA[i];
      cross.setAttribute("x1", XS[i]);
      cross.setAttribute("x2", XS[i]);
      cross.style.opacity = "1";

      tip.innerHTML =
        "<b>ความแข็งเกร็งหายไป " + d.k + "</b>" +
        '<span class="tip-key" style="background:var(--s1)"></span>อัตราส่วนการสั่น <i>' + d.t + "</i> — " + d.st + "<br>" +
        '<span class="tip-key" style="background:var(--s2)"></span>ความถี่ธรรมชาติ <i>' + d.fn + "</i> — " + d.sfn;

      var rect = svg.getBoundingClientRect();
      var scale = rect.width / VB_W;
      var x = XS[i] * scale;
      tip.classList.add("on");
      var tw = tip.offsetWidth;
      var left = Math.max(4, Math.min(x - tw / 2, rect.width - tw - 4));
      tip.style.left = left + "px";
      tip.style.top = "8px";
      void host;
    }

    function hide() {
      cross.style.opacity = "0";
      tip.classList.remove("on");
    }

    Array.prototype.forEach.call(svg.querySelectorAll("#sens-hit rect"), function (r) {
      var i = parseInt(r.getAttribute("data-i"), 10);
      r.addEventListener("mouseenter", function () { show(i, r); });
      r.addEventListener("touchstart", function (e) { show(i, r); e.stopPropagation(); }, { passive: true });
      r.addEventListener("focus", function () { show(i, r); });
      r.setAttribute("tabindex", "0");
    });
    svg.addEventListener("mouseleave", hide);
    svg.addEventListener("blur", hide, true);
  })();

  /* ---------- 7. fade-in ตอนเลื่อนถึง ---------- */
  var targets = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && targets.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    Array.prototype.forEach.call(targets, function (t) { io.observe(t); });
  } else {
    Array.prototype.forEach.call(targets, function (t) { t.classList.add("in"); });
  }
})();
