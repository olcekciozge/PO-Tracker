// Giriş ve parola sayfaları: parolayı göster/gizle, parola gücü, eşleşme kontrolü.
(function () {
  // Parolayı göster / gizle
  document.querySelectorAll("[data-po-reveal]").forEach(function (button) {
    var input = document.getElementById(button.getAttribute("data-po-reveal"));
    if (!input) return;
    button.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", show ? "true" : "false");
      button.setAttribute("aria-label", show ? "Parolayı gizle" : "Parolayı göster");
      input.focus();
    });
  });

  // Parola gücü çubuğu
  var labels = ["", "Zayıf", "Orta", "İyi", "Güçlü"];
  document.querySelectorAll("[data-po-strength]").forEach(function (input) {
    var meter = document.getElementById(input.getAttribute("data-po-strength"));
    var text = input.closest(".po-field").querySelector("[data-po-strength-label]");
    input.addEventListener("input", function () {
      var value = input.value;
      var score = 0;
      if (value.length >= 8) score++;
      if (value.length >= 12) score++;
      if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
      if (/\d/.test(value)) score++;
      if (/[^A-Za-z0-9]/.test(value)) score++;
      var level = value ? Math.max(1, Math.min(4, score - 1)) : 0;
      meter.setAttribute("data-level", level);
      if (text) text.textContent = level ? "Parola gücü: " + labels[level] : "";
    });
  });

  // İki parola aynı mı?
  document.querySelectorAll("[data-po-match]").forEach(function (input) {
    var first = document.getElementById(input.getAttribute("data-po-match"));
    var text = input.closest(".po-field").querySelector("[data-po-match-label]");
    function check() {
      if (!input.value) { text.textContent = ""; text.className = "po-match"; return; }
      var same = input.value === first.value;
      text.textContent = same ? "✓ Parolalar eşleşiyor" : "Parolalar eşleşmiyor";
      text.className = "po-match " + (same ? "is-ok" : "is-bad");
    }
    input.addEventListener("input", check);
    first.addEventListener("input", check);
  });
})();