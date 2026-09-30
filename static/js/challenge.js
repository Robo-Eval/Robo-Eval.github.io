/* Shared navigation behavior for the RoboEval site.
   Owns the mobile burger toggle and marks the current page in the navbar.
   Loaded by index.html and every challenge/* page. */
(function () {
  "use strict";

  // Which navbar entry to highlight for each page.
  var NAV_FOR_PAGE = {
    "index.html": "home",
    "": "home",
    "challenge.html": "challenge",
    "challenge-rules.html": "docs",
    "challenge-submission.html": "docs",
  };

  function currentPage() {
    var parts = window.location.pathname.split("/");
    return parts[parts.length - 1];
  }

  function markCurrent() {
    var key = NAV_FOR_PAGE[currentPage()];
    if (!key) return;
    var item = document.querySelector('.re-navbar [data-nav="' + key + '"]');
    if (item) item.classList.add("is-current");
  }

  function wireBurger() {
    var burgers = document.querySelectorAll(".re-navbar .navbar-burger");
    Array.prototype.forEach.call(burgers, function (burger) {
      burger.addEventListener("click", function () {
        var target = document.getElementById(burger.dataset.target);
        burger.classList.toggle("is-active");
        if (target) target.classList.toggle("is-active");
        burger.setAttribute(
          "aria-expanded",
          burger.classList.contains("is-active") ? "true" : "false"
        );
      });
    });
  }

  // On touch devices Bulma's is-hoverable dropdowns never open, so let a tap on
  // the parent link expand the menu instead of navigating away immediately.
  function wireTouchDropdowns() {
    if (!window.matchMedia || !window.matchMedia("(hover: none)").matches) return;
    var links = document.querySelectorAll(".re-navbar .navbar-item.has-dropdown > .navbar-link");
    Array.prototype.forEach.call(links, function (link) {
      link.addEventListener("click", function (event) {
        var parent = link.parentElement;
        if (!parent.classList.contains("is-active")) {
          event.preventDefault();
          parent.classList.add("is-active");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    markCurrent();
    wireBurger();
    wireTouchDropdowns();
  });
})();
