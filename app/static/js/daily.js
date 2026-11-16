/*
 * The daily puzzle page's behaviour (templates/daily/play.html).
 *
 * This file never knows the answer. It works like this:
 *   1. Draw the page from `state`, the JSON the server put in the page.
 *   2. Let the player type letters (on-screen keyboard or real keyboard).
 *      Typing is purely local until they press Enter.
 *   3. On Enter, POST the guess to /daily/guess. The server checks it,
 *      saves it and replies with a fresh `state`.
 *   4. Redraw everything from that new state.
 * So the rules (colours, when facts unlock, game over) all live on the server
 * in app/daily/game.py; this file only displays what it's told.
 */
(function () {
  "use strict";

  var config = window.DAILY_CONFIG;
  var state = JSON.parse(document.getElementById("daily-state").textContent);
  // The row being typed, not yet sent: one slot per letter ("" = empty),
  // and the slot the next letter goes into. Tapping a tile moves the cursor,
  // so any letter can be changed without deleting the ones after it.
  var slots = [];
  var cursor = 0;
  var sending = false;  // true while a guess is on its way to the server

  var KEY_ROWS = ["QWERTYUIOP", "ASDFGHJKL", "↵ZXCVBNM⌫"];
  var EMOJI = { hit: "🟩", close: "🟨", miss: "⬛" };
  var MARK_WORDS = { hit: "right place", close: "wrong place", miss: "not in the name" };

  function $(id) { return document.getElementById(id); }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  // ---- Drawing ------------------------------------------------------------

  function render(revealLastRow) {
    renderFacts();
    renderBoard(revealLastRow);
    renderKeyboard();
    renderResult();
    $("daily-length").textContent = state.length + " letters · " + state.max_guesses + " guesses";
  }

  // ---- Fitting the screen ---------------------------------------------------

  // .daily-play fills the screen from where it starts down to the bottom, so
  // the clues, board and keyboard are all visible without scrolling. The
  // board takes whatever height is left and sizes its tiles from it (CSS).
  // On short screens (phones) the site's menu bar would leave too little
  // room, so the play area takes the whole screen and the page scrolls past
  // the menu; scrolling up still reaches it.
  var SHORT_SCREEN = 760;

  function fitToScreen() {
    var play = $("daily-play");
    var top = play.getBoundingClientRect().top + window.scrollY;
    var short = window.innerHeight < SHORT_SCREEN;
    play.style.setProperty("--daily-top", (short ? 8 : top) + "px");
    play.classList.add("fitted");
    return short ? top - 8 : 0;
  }

  // ---- Light and dark -------------------------------------------------------

  // The page follows the device's setting until the player picks one with the
  // toggle; their pick is remembered in this browser. The saved pick is
  // applied by a tiny script at the top of play.html, before drawing.
  var THEME_KEY = "tactification-daily-theme";
  var page = document.querySelector(".daily");
  var themeButton = $("daily-theme");

  function currentTheme() {
    if (page.dataset.theme) return page.dataset.theme;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }

  function showThemeButton() {
    var other = currentTheme() === "dark" ? "light" : "dark";
    themeButton.setAttribute("aria-label", "Switch to " + other + " mode");
    themeButton.title = "Switch to " + other + " mode";
    themeButton.firstElementChild.className = "bi " + (other === "light" ? "bi-sun-fill" : "bi-moon-stars-fill");
  }

  themeButton.addEventListener("click", function (event) {
    var next = currentTheme() === "dark" ? "light" : "dark";
    page.dataset.theme = next;
    try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* not remembered, still switched */ }
    showThemeButton();
    if (event.detail > 0) themeButton.blur();  // keep Enter for guessing
  });

  // ---- How to play ----------------------------------------------------------

  var RULES_SEEN = "tactification-daily-rules-seen";
  var rules = $("daily-how");

  function showRules() {
    if (rules.showModal) rules.showModal();
    else rules.setAttribute("open", "");  // very old browsers: shown inline
  }

  $("daily-help").addEventListener("click", function (event) {
    // Opened by mouse or touch: don't hand focus back to the ? button on
    // close, or the next Enter would reopen the rules instead of guessing.
    rules.dataset.blurOnClose = event.detail > 0 ? "1" : "";
    showRules();
  });
  rules.addEventListener("close", function () {
    if (rules.dataset.blurOnClose && document.activeElement) document.activeElement.blur();
    try { localStorage.setItem(RULES_SEEN, "1"); } catch (e) { /* storage blocked: show again next time */ }
  });

  function firstVisit() {
    try { return !localStorage.getItem(RULES_SEEN); } catch (e) { return false; }
  }

  // The two fact slots: unlocked ones show the fact, locked ones say when
  // they'll open. state.facts only ever contains the unlocked facts.
  function renderFacts() {
    [0, 1].forEach(function (i) {
      var box = $("daily-fact-" + (i + 1));
      var unlocked = i < state.facts.length;
      box.className = "daily-clue" + (unlocked ? "" : " locked");
      box.textContent = "";
      box.append(el("div", "daily-clue-label", i === 0 ? "First fact" : "Second fact"));
      box.append(el("p", "daily-fact", unlocked
        ? state.facts[i]
        : "Unlocks after " + state.fact_unlock_after[i] + " guesses"));
    });
  }

  // One row per allowed guess. Played rows show the server's colours, the
  // next row shows what's being typed, the rest are empty.
  function renderBoard(revealLastRow) {
    var board = $("daily-board");
    board.textContent = "";
    for (var r = 0; r < state.max_guesses; r++) {
      var row = el("div", "daily-row");
      row.style.setProperty("--n", state.length);
      board.style.setProperty("--rows", state.max_guesses);
      var played = state.rows[r];
      var active = !played && r === state.rows.length && !state.over;
      var letters = played ? played.guess : active ? slots : "";
      if (played && revealLastRow && r === state.rows.length - 1) row.classList.add("revealed");

      for (var i = 0; i < state.length; i++) {
        var mark = played ? played.marks[i] : null;
        var tile = el("div", "daily-tile" + (mark ? " " + mark : letters[i] ? " filled" : ""), letters[i] || "");
        if (mark) {
          tile.setAttribute("aria-label", letters[i] + ", " + MARK_WORDS[mark]);
          tile.style.animationDelay = (i * 0.06) + "s";  // tiles flip one after another
        }
        if (active) addCursorControls(tile, i);
        row.append(tile);
      }
      board.append(row);
    }
  }

  // Each key shows the best result that letter has had so far
  // (green beats yellow beats grey).
  function renderKeyboard() {
    var rank = { hit: 3, close: 2, miss: 1 };
    var best = {};
    state.rows.forEach(function (row) {
      row.marks.forEach(function (mark, i) {
        var letter = row.guess[i];
        if (!best[letter] || rank[mark] > rank[best[letter]]) best[letter] = mark;
      });
    });

    var keyboard = $("daily-keyboard");
    keyboard.textContent = "";
    KEY_ROWS.forEach(function (keys) {
      var row = el("div", "daily-krow");
      keys.split("").forEach(function (key) {
        var isEnter = key === "↵", isBack = key === "⌫";
        var button = el("button", "daily-key" + (isEnter || isBack ? " wide" : "") + (best[key] ? " " + best[key] : ""),
          isEnter ? "Enter" : key);
        button.type = "button";
        button.disabled = state.over;
        button.setAttribute("aria-label", isEnter ? "Enter" : isBack ? "Delete" : key);
        button.tabIndex = -1;  // the real keyboard types directly; these are for touch and mouse
        button.addEventListener("mousedown", function (event) { event.preventDefault(); });  // don't take focus
        button.addEventListener("click", function () { press(isEnter ? "ENTER" : isBack ? "BACK" : key); });
        row.append(button);
      });
      keyboard.append(row);
    });
  }

  // Shown once the game is over: the answer, both facts, sources, share text.
  function renderResult() {
    var box = $("daily-result");
    box.hidden = !state.over;
    if (!state.over) return;

    var reveal = state.reveal;
    $("daily-result-title").textContent = state.won ? "Solved in " + state.rows.length : "The answer was";
    $("daily-answer").textContent = reveal.display;

    var facts = $("daily-answer-facts");
    facts.textContent = "";
    reveal.facts.forEach(function (fact) { facts.append(el("li", null, fact)); });

    var sources = $("daily-sources");
    // Only http(s) addresses become links (the admin form and the importer
    // also check this), so a bad source can never run script on click.
    var links = reveal.sources.map(function (url) {
      try { var parsed = new URL(url); } catch (e) { return null; }
      return /^https?:$/.test(parsed.protocol) ? parsed : null;
    }).filter(Boolean);
    sources.textContent = links.length ? "Read more: " : "";
    links.forEach(function (parsed, i) {
      var link = el("a", null, parsed.hostname.replace(/^www\./, "") + " ↗");
      link.href = parsed.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      if (i) sources.append(" · ");
      sources.append(link);
    });

    $("daily-share").value = shareText();
  }

  // Spoiler-free: colours only, never letters.
  function shareText() {
    var rows = state.rows.map(function (row) {
      return row.marks.map(function (mark) { return EMOJI[mark]; }).join("");
    });
    var score = (state.won ? state.rows.length : "X") + "/" + state.max_guesses;
    return "Tactification Daily #" + state.number + " " + score + "\n" + rows.join("\n") + "\n" + config.shareUrl;
  }

  function setStatus(text) { $("daily-status").textContent = text || ""; }

  function shakeRow() {
    var row = $("daily-board").children[state.rows.length];
    if (!row) return;
    row.classList.remove("shake");
    void row.offsetWidth;  // restart the animation if it's already shaking
    row.classList.add("shake");
  }

  // ---- Input --------------------------------------------------------------

  function resetSlots() {
    slots = [];
    for (var i = 0; i < state.length; i++) slots.push("");
    cursor = 0;
  }

  // A tile in the row being typed: tap it to put the cursor there.
  function addCursorControls(tile, i) {
    tile.classList.add("editable");
    if (i === cursor) tile.classList.add("cursor");
    tile.setAttribute("role", "button");
    tile.setAttribute("aria-label", "Letter " + (i + 1) + (slots[i] ? ", " + slots[i] : ", empty"));
    tile.addEventListener("click", function () {
      if (state.over || sending) return;
      cursor = i;
      renderBoard(false);
    });
  }

  function nextEmpty(from) {
    for (var i = from; i < state.length; i++) if (!slots[i]) return i;
    return state.length;  // past the end: every slot after `from` is filled
  }

  // key: a letter, "BACK", "ENTER", "LEFT" or "RIGHT".
  function press(key) {
    if (state.over || sending) return;
    if (key === "ENTER") {
      if (slots.indexOf("") !== -1) {
        setStatus("Needs " + state.length + " letters.");
        shakeRow();
        return;
      }
      submit(slots.join(""));
      return;
    }
    if (key === "BACK") {
      // Clear the letter under the cursor; on an empty slot, step back
      // and clear the one before it.
      if (cursor < state.length && slots[cursor]) {
        slots[cursor] = "";
      } else if (cursor > 0) {
        cursor -= 1;
        slots[cursor] = "";
      }
    } else if (key === "LEFT") {
      cursor = Math.max(0, cursor - 1);
    } else if (key === "RIGHT") {
      cursor = Math.min(state.length - 1, cursor + 1);
    } else if (cursor < state.length) {
      // Type over the slot, then move on to the next empty one (or the end).
      slots[cursor] = key;
      cursor = nextEmpty(cursor + 1);
    }
    setStatus("");
    renderBoard(false);
  }

  // Sends one guess. The server replies with the new state, or with an error
  // (e.g. wrong length) and the unchanged state.
  function submit(guess) {
    sending = true;
    var before = state.facts.length;
    fetch(config.guessUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({ guess: guess })
    })
      .then(function (response) {
        return response.json().then(function (body) { return { ok: response.ok, body: body }; });
      })
      .then(function (result) {
        if (result.body.state) state = result.body.state;
        if (!result.ok) {
          setStatus(result.body.error);
          shakeRow();
          render(false);
          return;
        }
        resetSlots();
        render(true);
        if (state.over) {
          // Let the last row finish flipping, then bring the result into view.
          setTimeout(function () { $("daily-result").scrollIntoView({ behavior: "smooth", block: "start" }); }, 900);
        }
        if (state.over) setStatus(state.won ? "Got it in " + state.rows.length + "." : "Out of guesses.");
        else if (state.facts.length > before) setStatus(state.facts.length === 1 ? "First fact unlocked." : "Second fact unlocked.");
        else {
          var left = state.max_guesses - state.rows.length;
          setStatus(left + (left === 1 ? " guess" : " guesses") + " left.");
        }
      })
      .catch(function () {
        setStatus("Couldn't reach the server. Check your connection and press Enter again.");
      })
      .then(function () { sending = false; });
  }

  // Real keyboard: letters, Backspace and Enter. Ignored while typing in the
  // share box or when a modifier is held (so Ctrl+C etc. still work).
  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (rules.open) return;  // the rules pop-up handles its own keys
    if (event.target.closest("textarea, input")) return;
    if (event.key === "Enter") {
      // Enter on a focused control (Copy, ?, theme) activates it; anywhere
      // else, including the on-screen keys, it sends the guess.
      var control = event.target.closest("button, a, [role=button]");
      if (control && !control.closest(".daily-key, .daily-tile")) return;
      event.preventDefault();
      press("ENTER");
    } else if (event.key === "Backspace" || event.key === "Delete") {
      event.preventDefault();
      press("BACK");
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      press(event.key === "ArrowLeft" ? "LEFT" : "RIGHT");
    } else if (/^[a-z]$/i.test(event.key)) {
      press(event.key.toUpperCase());
    }
  });

  $("daily-copy").addEventListener("click", function () {
    var box = $("daily-share");
    function copied() { $("daily-copy-status").textContent = "Copied. Paste it anywhere."; }
    function fallback() {
      box.focus();
      box.select();
      $("daily-copy-status").textContent = "Selected. Press Ctrl+C or ⌘C to copy.";
    }
    if (navigator.clipboard) navigator.clipboard.writeText(box.value).then(copied, fallback);
    else fallback();
  });

  resetSlots();
  showThemeButton();
  render(false);
  var scrollTo = fitToScreen();
  if (scrollTo > 0 && window.scrollY === 0) window.scrollTo(0, scrollTo);
  window.addEventListener("resize", fitToScreen);
  if (firstVisit() && !state.over) showRules();
})();
