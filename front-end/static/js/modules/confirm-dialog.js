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
