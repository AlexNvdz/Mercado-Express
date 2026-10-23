/* Staff panel only (templates/adminpanel/_layout.html): "/" jumps to the
 * global search, as in most admin tools, unless the user is already typing.
 */
const search = document.querySelector("[data-shortcut='/']");

if (search) {
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target;
    if (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
    event.preventDefault();
    search.focus();
    search.select();
  });
}
