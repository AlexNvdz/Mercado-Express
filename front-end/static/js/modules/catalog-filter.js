// --- Catalog categories: one list, a sidebar on wide screens and a
// collapsible menu on phones (templates/catalog/list.html). Without JS the
// <details> just starts closed everywhere.
var wide = window.matchMedia("(min-width: 901px)");
document.querySelectorAll("details[data-open-wide]").forEach(function (details) {
  var sync = function () {
    details.open = wide.matches;
  };
  sync();
  wide.addEventListener("change", sync);
});
