(function () {
    "use strict";

    // Inline icons so no external asset is needed. "currentColor" lets them
    // inherit the button's text color for light/dark themes.
    var COPY_ICON =
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" ' +
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
        'stroke-linejoin="round" aria-hidden="true">' +
        '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>' +
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>' +
        "</svg>";

    var CHECK_ICON =
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" ' +
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" ' +
        'stroke-linejoin="round" aria-hidden="true">' +
        '<polyline points="20 6 9 17 4 12"></polyline>' +
        "</svg>";

    function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        return new Promise(function (resolve, reject) {
            var ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.top = "-1000px";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try {
                document.execCommand("copy") ? resolve() : reject();
            } catch (err) {
                reject(err);
            } finally {
                document.body.removeChild(ta);
            }
        });
    }

    // Extract the source without the inline line-number spans. Cloning keeps
    // the visible code untouched while we strip ".linenos" for the copy.
    function codeFromPre(pre) {
        var clone = pre.cloneNode(true);
        clone.querySelectorAll(".linenos").forEach(function (el) {
            el.remove();
        });
        return clone.textContent.replace(/\n+$/, "");
    }

    function flash(button, iconHtml, extraClass) {
        button.innerHTML = iconHtml;
        if (extraClass) {
            button.classList.add(extraClass);
        }
        window.clearTimeout(button._psResetTimer);
        button._psResetTimer = window.setTimeout(function () {
            button.innerHTML = COPY_ICON;
            button.classList.remove("ps-copied");
        }, 2000);
    }

    // Add an icon copy button to a single ".highlight" code field. Works for
    // both captioned and plain code blocks, since both wrap a ".highlight pre".
    function addButton(highlight) {
        var pre = highlight.querySelector("pre");
        if (!pre || highlight.querySelector(".ps-copy-button")) {
            return;
        }

        var button = document.createElement("button");
        button.type = "button";
        button.className = "ps-copy-button";
        button.innerHTML = COPY_ICON;
        button.setAttribute("aria-label", "Copy code to clipboard");
        button.setAttribute("title", "Copy");

        button.addEventListener("click", function () {
            copyText(codeFromPre(pre)).then(
                function () {
                    flash(button, CHECK_ICON, "ps-copied");
                },
                function () {
                    flash(button, COPY_ICON);
                }
            );
        });

        highlight.appendChild(button);
    }

    function addButtons() {
        document.querySelectorAll("div.highlight").forEach(addButton);
    }

    if (document.readyState !== "loading") {
        addButtons();
    } else {
        document.addEventListener("DOMContentLoaded", addButtons);
    }
})();
