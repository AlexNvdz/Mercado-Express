// --- Refund-claim widget (templates/partials/support_chat.html) ---------
// One message, one decision: each submit posts to orders:claim, which asks
// the backend and answers with its verdict. Nothing is remembered between
// messages or pages. "Solicitar reembolso" on a delivered order's page
// ([data-claim-open]) opens the widget with that order chosen.
var root = document.querySelector("[data-claim]");
if (root) {
  var launcher = root.querySelector(".claim__launcher");
  var panel = root.querySelector(".claim__panel");
  var thread = root.querySelector(".claim__thread");
  var form = root.querySelector(".claim__form");
  var select = form.elements.order_id;
  var text = form.elements.mensaje;
  var send = form.querySelector(".claim__send");
  var ordersLoaded = null;
  var opener = null;
  var busy = false;

  var VERDICTS = {
    aprobado: { chip: "status--delivered", label: "Aprobado" },
    rechazado: { chip: "status--cancelled", label: "Rechazado" },
    revision_manual: {
      chip: "status--pending",
      label: "Sin resolver",
      hint: "No pudimos resolverlo automáticamente. Cuéntanos qué pasó y pide el reembolso de forma explícita para intentarlo de nuevo.",
    },
  };
  var FAILED = "No pudimos procesar tu reclamo. Intenta de nuevo.";
  var NO_ORDERS = "No tienes pedidos entregados para reclamar";

  root.hidden = false;
  document.querySelectorAll("[data-claim-open]").forEach(function (btn) { btn.hidden = false; });

  var el = function (tag, className, content) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (content) node.textContent = content;
    return node;
  };

  var addOption = function (id, number, created) {
    var option = el("option", "", created ? number + " · " + created : number);
    option.value = id;
    option.dataset.number = number;
    select.append(option);
  };
  // value "" explicitly: an option without one submits its text.
  var placeholder = function (label) {
    select.replaceChildren(el("option", "", label));
    select.firstChild.value = "";
    select.disabled = true;
  };

  var loadOrders = function () {
    if (ordersLoaded) return ordersLoaded;
    ordersLoaded = fetch(root.dataset.ordersUrl, { headers: { Accept: "application/json" } })
      .then(function (r) { return r.json().then(function (body) { return r.ok ? body : Promise.reject(body); }); })
      .then(function (body) {
        if (!body.orders.length) return placeholder(NO_ORDERS);
        select.replaceChildren();
        body.orders.forEach(function (o) { addOption(o.id, o.order_number, o.created); });
        select.disabled = false;
      })
      .catch(function (body) {
        ordersLoaded = null; // retry on the next open
        placeholder((body && body.error) || "No pudimos cargar tus pedidos");
      });
    return ordersLoaded;
  };

  var scrollDown = function () { thread.scrollTop = thread.scrollHeight; };
  var push = function (node) {
    node.classList.add("is-new");
    thread.append(node);
    scrollDown();
    return node;
  };

  var onKey = function (event) {
    if (event.key === "Escape") setOpen(false);
  };

  var setOpen = function (open, focusTarget) {
    root.classList.toggle("is-open", open);
    launcher.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      document.addEventListener("keydown", onKey);
      loadOrders();
      (focusTarget || (select.disabled ? text : select)).focus();
    } else {
      document.removeEventListener("keydown", onKey);
      (opener || launcher).focus();
      opener = null;
    }
  };

  launcher.addEventListener("click", function () { setOpen(!root.classList.contains("is-open")); });
  root.querySelector("[data-claim-close]").addEventListener("click", function () { setOpen(false); });
  // The phone scrim is ::before on the root: a click on it targets the root.
  root.addEventListener("click", function (event) { if (event.target === root) setOpen(false); });

  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-claim-open]");
    if (!btn) return;
    opener = btn;
    setOpen(true, text);
    loadOrders().then(function () {
      var id = btn.dataset.claimOpen;
      if (!select.querySelector('option[value="' + id + '"]')) {
        if (!select.value) select.replaceChildren(); // drop the "no orders" placeholder
        addOption(id, btn.dataset.claimNumber);
        select.disabled = false;
      }
      select.value = id;
    });
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (busy) return;
    var option = select.selectedOptions[0];
    if (!select.value) {
      push(el("li", "claim-msg claim-msg--bot", "Elige un pedido entregado para enviar tu reclamo."));
      return;
    }
    var body = new FormData(form); // before disabling: disabled fields are left out

    var mine = el("li", "claim-msg claim-msg--user");
    mine.append(el("span", "claim-msg__order", "Pedido " + option.dataset.number), text.value.trim());
    push(mine);
    var pending = push(el("li", "claim-msg claim-msg--bot claim-msg--pending"));
    var dots = el("span", "claim-dots");
    dots.setAttribute("aria-hidden", "true");
    dots.append(el("i"), el("i"), el("i"));
    pending.append(dots, "Analizando tu reclamo…");

    busy = true;
    send.disabled = select.disabled = true;
    send.textContent = "Analizando…";

    fetch(form.action, { method: "POST", body: body, headers: { Accept: "application/json" } })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) { return { ok: r.ok, data: data }; });
      })
      .catch(function () { return { ok: false, data: {} }; })
      .then(function (res) {
        pending.remove();
        var reply = el("li", "claim-msg claim-msg--bot");
        var verdict = res.ok && VERDICTS[res.data.decision];
        if (!verdict) {
          reply.append(el("span", "status status--cancelled", "No se envió"), el("p", "claim-msg__motivo", res.data.error || FAILED));
        } else {
          reply.append(el("span", "status " + verdict.chip, verdict.label), el("p", "claim-msg__motivo", res.data.motivo));
          if (verdict.hint) reply.append(el("p", "claim-msg__hint", verdict.hint));
          if (res.data.decision === "aprobado") {
            if (res.data.order_status_label) reply.append(el("p", "claim-msg__hint", "Estado del pedido: " + res.data.order_status_label + "."));
            option.remove(); // no longer delivered, nothing left to claim
            if (!select.options.length) placeholder(NO_ORDERS);
          }
          if (res.data.order_url) {
            var link = el("a", "claim-msg__link", "Ver pedido");
            link.href = res.data.order_url;
            reply.append(link);
          }
          text.value = "";
        }
        push(reply);
      })
      .finally(function () {
        busy = false;
        send.disabled = false;
        select.disabled = !select.value;
        send.textContent = "Enviar";
        text.focus();
      });
  });

  // Desktop chat convention: Enter sends, Shift+Enter breaks the line.
  text.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing || !matchMedia("(hover: hover)").matches) return;
    event.preventDefault();
    form.requestSubmit();
  });

  // Phones: keep the sheet above the on-screen keyboard, which covers the
  // layout viewport's bottom without resizing it on most mobile browsers.
  var vv = window.visualViewport;
  if (vv) {
    var fitKeyboard = function () {
      if (vv.scale > 1) return; // pinch zoom, not a keyboard
      root.style.setProperty("--claim-kb", Math.max(0, window.innerHeight - vv.height - vv.offsetTop) + "px");
    };
    vv.addEventListener("resize", fitKeyboard);
    vv.addEventListener("scroll", fitKeyboard);
  }
}
