// İç sayfalar: kaydırınca menü küçülür, başlık menüye geçer, üst alan solar.
(function () {
    // Grafik çubuklarının yüksekliği: data-hv="85" → --hv: 85
  document.querySelectorAll("[data-hv]").forEach(function (el) {
    el.style.setProperty("--hv", el.getAttribute("data-hv"));
  });
  var body = document.body;
  var hero = document.querySelector("[data-po-hero]");
  var mini = document.querySelector("[data-po-mini]");
  var toggle = document.querySelector("[data-po-nav-toggle]");

  // Telefonda menü aç/kapat
  if (toggle) {
    var menu = document.getElementById(toggle.getAttribute("aria-controls"));
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Sayfa başlığını menüdeki küçük başlığa kopyala
  if (hero && mini) {
    var title = hero.querySelector(".po-hero-title");
    if (title) mini.textContent = title.textContent.trim();
  }

  if (!hero) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ticking = false;

  function update() {
    ticking = false;
    var box = hero.getBoundingClientRect();
    var progress = (84 - box.top) / Math.max(1, box.height * 0.85);
    progress = Math.min(1, Math.max(0, progress));
    if (!reduceMotion) hero.style.setProperty("--hero-p", progress.toFixed(3));
    body.classList.toggle("po-nav-collapsed", progress > 0.9);
  }

  window.addEventListener("scroll", function () {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(update);
    }
  }, { passive: true });
  window.addEventListener("resize", update);
  update();
})();