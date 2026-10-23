// --- Toast auto-dismiss -------------------------------------------------
document.querySelectorAll(".toast").forEach(function (toast) {
  var close = function () {
    toast.classList.add("is-leaving");
    setTimeout(function () {
      toast.remove();
    }, 200);
  };
  var btn = toast.querySelector(".toast__close");
  if (btn) btn.addEventListener("click", close);
  setTimeout(close, 5000);
});
