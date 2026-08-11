/* Tollgate product landing */
(function () {
  // Reveal on scroll
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
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("visible"));
  }

  // Year
  const y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

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

  // Copy buttons
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const sel = btn.getAttribute("data-copy");
      const el = sel ? document.querySelector(sel) : null;
      const text = el ? el.innerText : btn.getAttribute("data-text") || "";
      try {
        await navigator.clipboard.writeText(text.trim());
        const prev = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(() => {
          btn.textContent = prev;
        }, 1400);
      } catch (_) {
        /* ignore */
      }
    });
  });

  // ── Live demo: Protect → Route → Prove ──
  const stage = document.getElementById("demo-stage");
  if (!stage) return;

  const scenes = ["protect", "route", "prove"];
  const buttons = stage.querySelectorAll(".demo-tabs button");
  const panels = stage.querySelectorAll(".scene");
  const progress = stage.querySelector(".demo-progress");
  let idx = 0;
  let timer = null;
  const INTERVAL = 5500;
  let paused = false;

  function show(i) {
    idx = ((i % scenes.length) + scenes.length) % scenes.length;
    const name = scenes[idx];
    buttons.forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-scene") === name);
    });
    panels.forEach((p) => {
      const on = p.getAttribute("data-scene") === name;
      p.classList.toggle("active", on);
      // retrigger bar animation
      if (on) {
        const bar = p.querySelector(".bar > i");
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

  // Prefer reduced motion: no auto-rotate
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  show(0);
  if (!reduce) start();
})();
