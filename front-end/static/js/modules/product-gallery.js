// --- Product detail gallery (templates/catalog/detail.html): a thumbnail
// shows its photo in the main well. Without JS the first photo stays.
document.querySelectorAll("[data-gallery]").forEach(function (gallery) {
  var main = gallery.querySelector("[data-gallery-main]");
  var thumbs = gallery.querySelectorAll("[data-gallery-src]");
  thumbs.forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      main.src = thumb.getAttribute("data-gallery-src");
      thumbs.forEach(function (t) {
        t.setAttribute("aria-current", t === thumb ? "true" : "false");
      });
    });
  });
});
