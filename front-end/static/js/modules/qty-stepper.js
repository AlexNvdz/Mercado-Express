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
