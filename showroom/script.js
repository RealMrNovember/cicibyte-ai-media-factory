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

  // The download button always points at the newest GitHub release; the static link is the fallback.
  function latestRelease() {
    if (!window.fetch) return;
    fetch("https://api.github.com/repos/RealMrNovember/cicibyte-ai-media-factory/releases/latest", { headers: { Accept: "application/vnd.github+json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (rel) {
        if (!rel || !rel.assets) return;
        var exe = rel.assets.filter(function (a) { return /Setup-[\d.]+\.exe$/.test(a.name); })[0];
        if (!exe) return;
        var links = document.querySelectorAll("[data-mf-download]");
        for (var i = 0; i < links.length; i++) links[i].setAttribute("href", exe.browser_download_url);
        var tags = document.querySelectorAll("[data-mf-version]");
        for (var j = 0; j < tags.length; j++) tags[j].textContent = rel.tag_name;
        var sizes = document.querySelectorAll("[data-mf-size]");
        for (var k = 0; k < sizes.length; k++) sizes[k].textContent = Math.round(exe.size / 1048576) + " MB";
      })
      .catch(function () { /* offline or rate-limited: keep the static link */ });
  }
  latestRelease();

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage unavailable */ }
  setLang(saved || "en");

  document.addEventListener("click", function (ev) {
    var langBtn = ev.target.closest("[data-set-lang]");
    if (langBtn) { setLang(langBtn.getAttribute("data-set-lang")); return; }

    var tab = ev.target.closest("[data-shot]");
    if (tab) {
      var name = tab.getAttribute("data-shot");
      document.querySelectorAll("[data-shot]").forEach(function (b) { b.setAttribute("aria-selected", String(b === tab)); });
      document.querySelectorAll("[data-shot-img]").forEach(function (img) { img.hidden = img.getAttribute("data-shot-img") !== name; });
      document.querySelectorAll("[data-shot-caption]").forEach(function (c) { c.hidden = c.getAttribute("data-shot-caption") !== name; });
      return;
    }

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
