/* Tollgate product site */
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
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("visible"));
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

  // Year
  const y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

  // Copy install snippet
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
})();
