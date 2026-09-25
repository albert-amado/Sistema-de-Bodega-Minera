(function() {
    "use strict";

    var STORAGE_KEY = "a11yPrefs";
    var root = document.documentElement;

    var defaults = {
        grayscale: false,
        invert: false,
        saturate: false,
        links: false,
        fontSize: 100, // %
        lineHeight: 15 // *0.1 -> 1.5
    };

    var state = Object.assign({}, defaults, loadPrefs());

    var fab = document.getElementById("a11y-fab");
    var dock = document.getElementById("a11y-dock");
    var closeBtn = document.getElementById("a11y-close");
    var resetBtn = document.getElementById("a11y-reset");
    var fontInput = document.getElementById("a11y-fontsize");
    var lineInput = document.getElementById("a11y-lineheight");
    var toggleButtons = dock.querySelectorAll("[data-toggle]");

    function loadPrefs() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function savePrefs() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (e) {
            /* almacenamiento no disponible: los ajustes no persisten entre páginas */
        }
    }

    // ---- filtros visuales combinados ----
    function applyFilters() {
        var parts = [];
        if (state.grayscale) parts.push("grayscale(1)");
        if (state.invert) parts.push("invert(1) hue-rotate(180deg)");
        if (state.saturate) parts.push("saturate(0.45)");
        root.style.filter = parts.length ? parts.join(" ") : "";
    }

    function applyLinks() {
        root.classList.toggle("a11y-links", state.links);
    }

    function applyFontSize() {
        root.style.fontSize = state.fontSize + "%";
    }

    function applyLineHeight() {
        // 10..30 -> 1.0..3.0
        var value = (state.lineHeight / 10).toFixed(1);
        root.style.setProperty("--a11y-line-height", value);
        root.style.lineHeight = value;
    }

    function syncControls() {
        toggleButtons.forEach(function(btn) {
            var key = btn.dataset.toggle;
            btn.setAttribute("aria-checked", String(!!state[key]));
        });
        fontInput.value = state.fontSize;
        document.querySelector('output[for="a11y-fontsize"]').textContent = state.fontSize + "%";
        lineInput.value = state.lineHeight;
        document.querySelector('output[for="a11y-lineheight"]').textContent = (state.lineHeight / 10).toFixed(1);
    }

    function applyAll() {
        applyFilters();
        applyLinks();
        applyFontSize();
        applyLineHeight();
        syncControls();
    }

    // ---- interacciones ----
    toggleButtons.forEach(function(btn) {
        btn.addEventListener("click", function() {
            var key = btn.dataset.toggle;
            state[key] = !state[key];
            applyAll();
            savePrefs();
        });
    });

    fontInput.addEventListener("input", function() {
        state.fontSize = Number(fontInput.value);
        applyAll();
        savePrefs();
    });

    lineInput.addEventListener("input", function() {
        state.lineHeight = Number(lineInput.value);
        applyAll();
        savePrefs();
    });

    resetBtn.addEventListener("click", function() {
        state = Object.assign({}, defaults);
        applyAll();
        savePrefs();
    });

    function openDock() {
        dock.hidden = false;
        fab.setAttribute("aria-expanded", "true");
    }

    function closeDock() {
        dock.hidden = true;
        fab.setAttribute("aria-expanded", "false");
    }

    fab.addEventListener("click", function() {
        dock.hidden ? openDock() : closeDock();
    });
    closeBtn.addEventListener("click", closeDock);

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape" && !dock.hidden) closeDock();
    });
    document.addEventListener("click", function(e) {
        if (!dock.hidden && !dock.contains(e.target) && e.target !== fab && !fab.contains(e.target)) {
            closeDock();
        }
    });

    // ---- estado inicial (persistente entre páginas) ----
    applyAll();
})();