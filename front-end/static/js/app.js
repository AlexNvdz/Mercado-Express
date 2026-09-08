/* MercadoExpress -- small progressive-enhancement helpers.
 * No framework: this project is server-rendered Django templates. Every
 * feature here degrades gracefully (forms submit normally without JS).
 */
(function () {
  "use strict";

  // --- Mobile nav toggle -----------------------------------------------
  var toggle = document.querySelector(".navbar__toggle");
  var links = document.querySelector(".navbar__links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var isOpen = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

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

  // --- Quantity steppers (any <div class="qty-stepper"> with a number input)
  document.querySelectorAll(".qty-stepper").forEach(function (stepper) {
    var input = stepper.querySelector("input[type=number]");
    if (!input) return;
    var min = parseInt(input.getAttribute("min") || "1", 10);
    var max = input.getAttribute("max") ? parseInt(input.getAttribute("max"), 10) : null;

    stepper.querySelectorAll("button[data-step]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var step = parseInt(btn.getAttribute("data-step"), 10);
        var next = (parseInt(input.value, 10) || min) + step;
        if (next < min) next = min;
        if (max !== null && next > max) next = max;
        input.value = next;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    });
  });
})();
