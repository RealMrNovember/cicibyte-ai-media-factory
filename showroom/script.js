(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "mf-lang";

  function setLang(lang) {
    if (lang !== "en" && lang !== "tr") lang = "en";
    root.setAttribute("lang", lang);
    var buttons = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", String(buttons[i].getAttribute("data-set-lang") === lang));
    }
    try { localStorage.setItem(KEY, lang); } catch (e) { /* storage unavailable */ }
  }

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage unavailable */ }
  setLang(saved || "en");

  document.addEventListener("click", function (ev) {
    var langBtn = ev.target.closest("[data-set-lang]");
    if (langBtn) { setLang(langBtn.getAttribute("data-set-lang")); return; }

    var copyBtn = ev.target.closest("[data-copy-target]");
    if (copyBtn) {
      var el = document.getElementById(copyBtn.getAttribute("data-copy-target"));
      if (!el) return;
      var text = el.innerText.trim();
      var done = function () {
        copyBtn.classList.add("is-copied");
        setTimeout(function () { copyBtn.classList.remove("is-copied"); }, 1800);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
      } else { fallback(text); done(); }
    }
  });

  function fallback(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* ignore */ }
    document.body.removeChild(ta);
  }

  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());
})();
