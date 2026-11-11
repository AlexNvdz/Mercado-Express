// Address form: suggests the chosen department's cities (Envia's list,
// through dashboard:address_cities) in the city field's <datalist>. Without
// JS the field is plain text and the backend still validates the city.
const form = document.querySelector("[data-address-form]");
const state = form?.querySelector("[name=state]");
const options = document.getElementById("city-options");

if (form && state && options) {
  const load = () => {
    const wanted = state.value;
    options.replaceChildren();
    if (!wanted) return;
    void fetch(`${form.dataset.citiesUrl}?departamento=${encodeURIComponent(wanted)}`)
      .then((response) => (response.ok ? response.json() : []))
      .then((cities) => {
        // A slower answer for a department the user already left.
        if (state.value === wanted) options.replaceChildren(...cities.map((name) => new Option(name)));
      })
      .catch(() => {});
  };
  state.addEventListener("change", load);
  load();
}
