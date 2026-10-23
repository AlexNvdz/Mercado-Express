// --- Mobile account menu toggle -----------------------------------------
var toggle = document.querySelector(".navbar__toggle");
var links = document.querySelector(".navbar__links");
if (toggle && links) {
  toggle.addEventListener("click", function () {
    var isOpen = links.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
}

// --- Categories dropdown: close on outside click / Escape --------------
document.querySelectorAll("details.navdrop").forEach(function (drop) {
  document.addEventListener("click", function (event) {
    if (drop.open && !drop.contains(event.target)) drop.open = false;
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && drop.open) {
      drop.open = false;
      drop.querySelector("summary").focus();
    }
  });
});
