/* Tollgate — admission desk */
(function () {
  const reveals = document.querySelectorAll(".reveal");
  if (reveals.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -30px 0px" }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("visible"));
  }

  const y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

  // UTC clock on console
  const clock = document.getElementById("console-clock");
  if (clock) {
    const tick = () => {
      const d = new Date();
      clock.textContent =
        d.toISOString().slice(11, 19) + "Z";
    };
    tick();
    setInterval(tick, 1000);
  }

  // Docs filter
  const input = document.getElementById("doc-filter");
  const cards = document.querySelectorAll("[data-doc]");
  if (input && cards.length) {
    input.addEventListener("input", () => {
      const q = (input.value || "").trim().toLowerCase();
      cards.forEach((c) => {
        const hay = (c.getAttribute("data-doc") || "").toLowerCase();
        c.style.display = !q || hay.includes(q) ? "" : "none";
      });
    });
  }

  let toastEl = null;
  function toast(msg, ok) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "toast";
      toastEl.setAttribute("role", "status");
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.toggle("err", !ok);
    toastEl.classList.add("show");
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(() => toastEl.classList.remove("show"), 1700);
  }

  function plainFrom(el) {
    if (!el) return "";
    return (el.innerText || el.textContent || "").replace(/\u00a0/g, " ").trim();
  }

  function copyFallback(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, text.length);
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (_) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  async function copyText(text) {
    text = (text || "").trim();
    if (!text) return false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (_) {}
    }
    return copyFallback(text);
  }

  function selectElementText(el) {
    if (!el) return;
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const sel = btn.getAttribute("data-copy");
      const el = sel ? document.querySelector(sel) : null;
      const text =
        (el ? plainFrom(el) : "") ||
        btn.getAttribute("data-text") ||
        "";
      if (el) selectElementText(el);
      const ok = await copyText(text);
      const prev = btn.getAttribute("data-label") || btn.textContent;
      btn.setAttribute("data-label", prev);
      btn.textContent = ok ? "Copied" : "Select+C";
      btn.classList.toggle("copied", ok);
      toast(ok ? "Copied" : "Selected — press ⌘C / Ctrl+C", ok);
      setTimeout(() => {
        btn.textContent = prev;
        btn.classList.remove("copied");
      }, 1500);
    });
  });

  document.querySelectorAll("[data-copy-href]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const href =
        btn.getAttribute("data-copy-href") || btn.getAttribute("href") || "";
      const ok = await copyText(href);
      toast(ok ? "Link copied" : "Copy failed", ok);
    });
  });

  document.querySelectorAll("pre.copyable, .term pre").forEach((pre) => {
    pre.setAttribute("tabindex", "0");
    pre.title = "Click to select — ⌘C / Ctrl+C";
    pre.addEventListener("click", () => selectElementText(pre));
  });

  // Demo rotation
  const stage = document.getElementById("demo-stage");
  if (!stage) return;

  const scenes = ["protect", "route", "prove"];
  const buttons = stage.querySelectorAll(".tabs button");
  const panels = stage.querySelectorAll(".scene");
  const progress = stage.querySelector(".progress");
  let idx = 0;
  let timer = null;
  const INTERVAL = 5600;
  let paused = false;

  function show(i) {
    idx = ((i % scenes.length) + scenes.length) % scenes.length;
    const name = scenes[idx];
    buttons.forEach((b) => {
      const on = b.getAttribute("data-scene") === name;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    panels.forEach((p) => {
      const on = p.getAttribute("data-scene") === name;
      p.classList.toggle("active", on);
      if (on) {
        const bar = p.querySelector(".meter > i");
        if (bar) {
          bar.style.width = "0";
          void bar.offsetWidth;
          bar.style.width = "100%";
        }
      }
    });
    if (progress) {
      progress.classList.remove("running");
      void progress.offsetWidth;
      if (!paused) progress.classList.add("running");
    }
  }

  function next() {
    show(idx + 1);
  }
  function start() {
    stop();
    if (paused) return;
    progress && progress.classList.add("running");
    timer = setInterval(next, INTERVAL);
  }
  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
    progress && progress.classList.remove("running");
  }

  buttons.forEach((b) => {
    b.addEventListener("click", () => {
      const name = b.getAttribute("data-scene");
      const i = scenes.indexOf(name);
      if (i >= 0) {
        show(i);
        start();
      }
    });
  });

  stage.addEventListener("mouseenter", () => {
    paused = true;
    stop();
  });
  stage.addEventListener("mouseleave", () => {
    paused = false;
    start();
  });

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  show(0);
  if (!reduce) start();
})();
