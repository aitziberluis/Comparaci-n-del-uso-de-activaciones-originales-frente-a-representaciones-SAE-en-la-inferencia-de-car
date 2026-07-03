/* SAE Feature Browser — vanilla JS, no build step. */
(function () {
  "use strict";

  var state = { data: null, charId: null, featureKey: null };

  /* ---- minimal Lucide-style icons (stroke = currentColor) ---- */
  var ICONS = {
    "venus-mars": '<circle cx="9.5" cy="9.5" r="4.2"/><circle cx="15" cy="15" r="4.2"/>',
    calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    sparkles: '<path d="M11.5 3.5 13 8l4.5 1.5L13 11l-1.5 4.5L10 11 5.5 9.5 10 8z"/><path d="M18 14l.8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8z"/>',
    brain: '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10M12 3v18M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    compass: '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'
  };
  function icon(name, cls) {
    return '<svg class="' + (cls || "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || ICONS.sparkles) + "</svg>";
  }

  /* ---- helpers ---- */
  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  function fmtInt(n) { return (n == null ? "—" : Number(n).toLocaleString("en-US")); }
  function pct(x) { return (x == null ? "—" : (x * 100).toFixed(1) + "%"); }

  // Highlight word-initial occurrences of the feature's top tokens (>=3 chars).
  function highlight(text, tokens) {
    var safe = esc(text);
    if (!tokens || !tokens.length) return safe;
    var seen = {}, list = [];
    tokens.forEach(function (t) {
      t = (t || "").toLowerCase();
      if (t.length >= 3 && !seen[t] && !/^(amp|lt|gt|quot)$/.test(t)) { seen[t] = 1; list.push(t); }
    });
    if (!list.length) return safe;
    list.sort(function (a, b) { return b.length - a.length; });
    var re = new RegExp("(^|[^A-Za-z])(" + list.map(escRe).join("|") + ")", "gi");
    return safe.replace(re, function (m, pre, tok) { return pre + "<mark>" + tok + "</mark>"; });
  }

  function characteristic() {
    return state.data.characteristics.filter(function (c) { return c.id === state.charId; })[0];
  }
  function featureByKey(c, key) {
    var found = null;
    c.poles.forEach(function (p) {
      p.features.forEach(function (f) {
        if (c.id + "|" + p.class_index + "|" + f.latent_id === key) found = { pole: p, feature: f };
      });
    });
    return found;
  }

  /* ---- render: tabs ---- */
  function renderTabs() {
    var tabs = el("tabs");
    tabs.innerHTML = "";
    state.data.characteristics.forEach(function (c) {
      var b = document.createElement("button");
      b.className = "tab";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", c.id === state.charId ? "true" : "false");
      b.innerHTML = icon(c.icon, "tab-ic") + "<span>" + esc(c.label) + "</span><small>" + esc(c.short) + "</small>";
      b.addEventListener("click", function () { selectChar(c.id); });
      tabs.appendChild(b);
    });
  }

  /* ---- render: characteristic header ---- */
  function renderHead(c) {
    var mi = c.model_info;
    var head = el("charHead");
    head.innerHTML =
      '<div class="ch-top">' +
        '<div>' +
          "<h1>" + esc(c.label) + "</h1>" +
          '<p class="question">' + esc(c.question) + "</p>" +
        "</div>" +
        '<div class="badges">' +
          '<span class="badge model">' + esc(c.model) + " · L" + mi.layer + "</span>" +
          '<span class="badge">SAE · ' + fmtInt(c.num_latents) + " latents</span>" +
          '<span class="badge">' + fmtInt(c.num_users_train) + " users · " + fmtInt(c.num_comments_train) + " comments</span>" +
        "</div>" +
      "</div>" +
      '<div class="metrics">' +
        metric(pct(c.metrics.accuracy), "Accuracy") +
        metric(pct(c.metrics.balanced_accuracy), "Balanced acc.", true) +
        metric(pct(c.metrics.f1_macro), "F1 macro", true) +
        metric(String(c.poles.length), "Classes", true) +
      "</div>";
  }
  function metric(val, lab, muted) {
    return '<div class="metric"><span class="val' + (muted ? " muted" : "") + '">' + val + '</span><span class="lab">' + lab + "</span></div>";
  }

  /* ---- render: features pane ---- */
  function renderFeatures(c) {
    var pane = el("featuresPane");
    pane.innerHTML = "";
    c.poles.forEach(function (p) {
      var maxScore = Math.max.apply(null, p.features.map(function (f) { return Math.abs(f.score) || 0; }).concat([1]));
      var group = document.createElement("div");
      group.className = "pole";
      group.style.setProperty("--tone", "var(--tone-" + p.tone + ")");
      group.innerHTML =
        '<div class="pole-head">' +
          '<span class="pole-dot"></span>' +
          '<span class="pole-name">' + esc(p.label) + "</span>" +
          '<span class="pole-tag">' + esc(p.tag) + "</span>" +
        "</div>";
      p.features.forEach(function (f) {
        var key = c.id + "|" + p.class_index + "|" + f.latent_id;
        var w = Math.round((Math.abs(f.score) / maxScore) * 100);
        var chips = f.top_words.slice(0, 5).map(function (t) { return '<span class="chip">' + esc(t) + "</span>"; }).join("");
        var btn = document.createElement("button");
        btn.className = "feat" + (key === state.featureKey ? " active" : "");
        btn.style.setProperty("--tone", "var(--tone-" + p.tone + ")");
        btn.dataset.key = key;
        btn.innerHTML =
          '<div class="feat-top"><span class="feat-name">' + esc(f.name) + '</span><span class="feat-id">#' + f.latent_id + "</span></div>" +
          '<div class="feat-desc">' + esc(f.description) + "</div>" +
          '<div class="chips">' + chips + "</div>" +
          '<div class="weight"><span style="width:' + w + '%"></span></div>' +
          '<span class="weight-lab">classifier weight ' + Number(f.coefficient).toFixed(1) + "</span>";
        btn.addEventListener("click", function () { selectFeature(key); });
        group.appendChild(btn);
      });
      pane.appendChild(group);
    });
  }

  /* ---- render: examples pane ---- */
  function renderExamples(c) {
    var head = el("examplesHead");
    var pane = el("examplesPane");
    var sel = featureByKey(c, state.featureKey);
    if (!sel) { head.innerHTML = ""; pane.innerHTML = ""; return; }
    var f = sel.feature, p = sel.pole;
    var legend = f.top_words.slice(0, 6).map(function (t) { return '<span class="legend-tok">' + esc(t) + "</span>"; }).join(" ");
    head.innerHTML =
      '<p class="eh-name">' + esc(f.name) + "</p>" +
      '<div class="eh-meta">' +
        '<span class="badge" style="color:#fff;background:var(--tone-' + p.tone + ');border-color:transparent">' + esc(p.tag) + "</span>" +
        '<span class="badge">latent #' + f.latent_id + "</span>" +
        '<span class="badge">' + esc(c.model) + "</span>" +
      "</div>" +
      '<p class="eh-desc">' + esc(f.description) + "</p>" +
      '<div class="eh-legend">Top activating tokens: ' + (legend || "<em>none</em>") + "</div>";

    if (!f.examples.length) {
      pane.innerHTML = '<p class="empty-note">This feature produced no positive example comments in the evaluation set — it carries weight in the classifier but rarely fires on real text.</p>';
      return;
    }
    var maxAct = Math.max.apply(null, f.examples.map(function (e) { return e.activation || 0; }).concat([0.0001]));
    pane.innerHTML = f.examples.map(function (e, i) {
      var bar = Math.round((e.activation / maxAct) * 100);
      return '<div class="ex">' +
        '<div class="ex-act"><span class="num">' + Number(e.activation).toFixed(1) + '</span>' +
          '<span class="bar"><span style="width:' + bar + '%"></span></span>' +
          '<span class="ex-rank">#' + (i + 1) + "</span></div>" +
        '<div class="ex-text">' + highlight(e.text, f.highlight) + "</div>" +
      "</div>";
    }).join("");
  }

  /* ---- render: explanation ---- */
  function renderExplain(c) {
    var poleNames = c.poles.map(function (p) { return p.label; });
    var human;
    if (c.poles.length === 2) {
      human = "<strong>" + esc(poleNames[0]) + "</strong> or <strong>" + esc(poleNames[1]) + "</strong>";
    } else {
      human = "one of <strong>" + poleNames.length + " " + esc(c.short.toLowerCase()) + " bands</strong>";
    }
    var direction = c.poles.length === 2
      ? "Features grouped under <strong>" + esc(poleNames[0]) + "</strong> push the prediction toward that class; features under <strong>" + esc(poleNames[1]) + "</strong> push the other way."
      : "Each group of features pushes the prediction toward its own age band.";

    el("explain").innerHTML =
      "<h3>So… can a few features tell " + human + "?</h3>" +
      "<p>The classifier never reads the raw text. It only sees <strong>how strongly each SAE feature fires</strong>, averaged across everything a person wrote. " +
      direction + " " +
      "Read down the lists on the left: if someone's comments keep lighting up the features on one side, the model leans that way. " +
      "On held-out users this reaches <strong>" + pct(c.metrics.accuracy) + " accuracy</strong> (" + pct(c.metrics.balanced_accuracy) + " balanced), using the " +
      "<strong>" + esc(c.model) + "</strong> sparse autoencoder.</p>" +
      '<p class="caveat">Reality check: many of the most influential features key on <em>surface cues</em> — topic words, ' +
      'self-reported MBTI codes like “INFJ”, or even orthographic fragments — rather than deep psychological signal. ' +
      "That is exactly what this dashboard is for: making visible <em>what</em> the SAE actually picked up on, so a high score can be interpreted instead of trusted blindly.</p>";
  }

  /* ---- selection ---- */
  function selectFeature(key) {
    state.featureKey = key;
    var c = characteristic();
    // toggle active class without full re-render
    var btns = document.querySelectorAll(".feat");
    for (var i = 0; i < btns.length; i++) btns[i].classList.toggle("active", btns[i].dataset.key === key);
    renderExamples(c);
    el("examplesPane").parentNode.scrollIntoView ? null : null;
  }

  function selectChar(id) {
    state.charId = id;
    var c = characteristic();
    // default to first feature of first pole
    var p0 = c.poles[0], f0 = p0.features[0];
    state.featureKey = c.id + "|" + p0.class_index + "|" + f0.latent_id;
    renderTabs();
    renderHead(c);
    renderFeatures(c);
    renderExamples(c);
    renderExplain(c);
    if (location.hash !== "#" + id && history.replaceState) history.replaceState(null, "", "#" + id);
  }

  window.addEventListener("hashchange", function () {
    if (!state.data) return;
    var hash = (location.hash || "").replace("#", "");
    if (hash && hash !== state.charId && state.data.characteristics.some(function (c) { return c.id === hash; })) {
      selectChar(hash);
    }
  });

  /* ---- boot ---- */
  fetch("data/site_data.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      state.data = data;
      var hash = (location.hash || "").replace("#", "");
      var ok = data.characteristics.some(function (c) { return c.id === hash; });
      selectChar(ok ? hash : data.characteristics[0].id);
    })
    .catch(function (err) {
      el("charHead").innerHTML = '<p style="color:#b00">Could not load data/site_data.json — ' + esc(err.message) + "</p>";
    });
})();
