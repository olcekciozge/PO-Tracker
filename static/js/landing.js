// Ana sayfa: fareyi gezdirince rozetler ve kart hafifçe kayar (parallax).
(function () {
  var hero = document.querySelector(".lp-hero");
  if (!hero) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var frame = null;

  hero.addEventListener("mousemove", function (event) {
    var box = hero.getBoundingClientRect();
    var mx = ((event.clientX - box.left) / box.width) * 2 - 1;
    var my = ((event.clientY - box.top) / box.height) * 2 - 1;

    if (frame) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(function () {
      hero.style.setProperty("--mx", mx.toFixed(3));
      hero.style.setProperty("--my", my.toFixed(3));
    });
  });

  hero.addEventListener("mouseleave", function () {
    hero.style.setProperty("--mx", 0);
    hero.style.setProperty("--my", 0);
  });
})();