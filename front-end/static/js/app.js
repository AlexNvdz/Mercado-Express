/* MercadoExpress -- small progressive-enhancement helpers.
 * No framework: this project is server-rendered Django templates. Every
 * feature here degrades gracefully (forms submit normally without JS).
 */
(function () {
  "use strict";

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

  // --- Confirmation dialog (forms with data-confirm) ----------------------
  // Replaces the browser's native confirm() with the styled <dialog> from
  // templates/partials/confirm_dialog.html. Without JS (or without <dialog>
  // support) the form simply submits, as before.
  var dialog = document.getElementById("confirm-dialog");
  if (dialog && typeof dialog.showModal === "function") {
    var titleEl = dialog.querySelector(".confirm__title");
    var messageEl = dialog.querySelector(".confirm__message");
    var okBtn = dialog.querySelector("[data-confirm-ok]");
    var cancelBtn = dialog.querySelector("[data-confirm-cancel]");
    var pending = null;

    var fill = function (text, form) {
      if (!text) return "";
      var select = form.querySelector("select[name=status]");
      var label = select && select.selectedIndex >= 0 ? select.options[select.selectedIndex].text : "";
      return text.replace("{status}", label);
    };

    document.addEventListener("submit", function (event) {
      var form = event.target;
      if (!form.matches || !form.matches("form[data-confirm]")) return;
      if (form.dataset.confirmed === "1") {
        delete form.dataset.confirmed;
        return;
      }
      event.preventDefault();
      pending = { form: form, submitter: event.submitter || null };

      var danger = form.dataset.confirmTone === "danger";
      dialog.classList.toggle("confirm--danger", danger);
      titleEl.textContent = fill(form.dataset.confirmTitle, form) || "¿Confirmas esta acción?";
      messageEl.textContent = fill(form.dataset.confirm, form);
      okBtn.textContent = form.dataset.confirmOk || "Confirmar";
      okBtn.className = danger ? "btn btn--danger-solid" : "btn";
      cancelBtn.textContent = form.dataset.confirmCancel || "Volver";
      dialog.showModal();
      cancelBtn.focus();
    });

    // Click on the backdrop (outside the box) closes like "Volver".
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close("cancel");
    });

    dialog.addEventListener("close", function () {
      var job = pending;
      pending = null;
      if (!job || dialog.returnValue !== "ok") {
        if (job && job.submitter) job.submitter.focus();
        return;
      }
      job.form.dataset.confirmed = "1";
      if (typeof job.form.requestSubmit === "function") {
        job.form.requestSubmit(job.submitter || undefined);
      } else {
        job.form.submit();
      }
    });
  }
})();
