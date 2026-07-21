(function () {
    "use strict";

    var SELECTOR = [
        "aside.footnote a.reference.external",
        ".citation a.reference.external",
    ].join(", ");

    function openInNewTab() {
        document.querySelectorAll(SELECTOR).forEach(function (link) {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
        });
    }

    if (document.readyState !== "loading") {
        openInNewTab();
    } else {
        document.addEventListener("DOMContentLoaded", openInNewTab);
    }
})();
