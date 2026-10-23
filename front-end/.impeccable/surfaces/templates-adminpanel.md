---
version: 1
slug: "templates-adminpanel"
primary_target: "templates/adminpanel"
related_targets: ["templates/catalog"]
---

# Staff panel (/panel/ and /catalogo/admin/)

Mode: Operate. Audience: store staff (employee/admin) on desktop and phone, working through 98k orders, 96k customers and 33k products. Job: find any record in seconds, act on what is waiting (orders by stage, stock under reorder level), correct statuses, keep stock and catalog right. Constraints: Django templates, vanilla JS, no build step; standard web controls; Spanish copy; pinned green identity (PRODUCT.md). CSS and JS split into organized files (user request).

Chosen direction: "Boletín de precios" (assigned by the roll, picked by the user 2026-10-22, sketch .impeccable/mocks/decision/assigned.html). Memorable moment: every key figure carries its variation against a reference, the way the wholesale price bulletin prints its variation column.

Unresolved: storefront redesign comes after the panel, in the same world or its own round.

## Direction contract

THESIS: The panel reads like the daily wholesale price bulletin (SIPSA/Corabastos): grouped, hairline-ruled tables where each key figure sits beside its variation against a reference. It refuses the category default of floating metric cards over one generic table.

OWN-WORLD: Pinned greens as a fixed 11-step ramp (g0 #f7faf6 to g10 #17382a), the only neutrals; volt #2e7d50 for actions, lime #c8e46e for selection and the brand mark, rose/amber/sky only for state. Archivo: normal width for text, condensed caps for band and column heads, tabular figures everywhere. Solid forest rail, white sheets ruled in 1px hairlines, 4-6px radii, no shadows, no gradients. Raises: hairline-joined modules (from the high-density mosaic), the 11-step ramp (exposure record), real elapsed time between status changes (labanotation), flat committed colour (zoo map), the code first in every row (fair catalog).

STORY: Staff land on what needs action, find any order, customer or SKU through one search, act in place, and trust that totals come from the sales ledger.

FIRST VIEWPORT: 232px forest rail with grouped nav and live counts; 60px white bar with the global search ("Buscar pedido, cliente o SKU") and date/user; title row; one joined strip of five figures with their variation lines; below, two ruled sheets: orders to attend grouped under forest bands by stage with an "Espera" variation column, and low stock with its variation against the reorder level. Rows link to their record; each sheet links to its full list.

FORM: assigned direction, position 3 of the ordered grounded list (shelf label, transit wayfinding, price bulletin, thermal receipt, dispatch manifest, offers flyer, crate stencil). seed:61946e163484869d. Signature move: the Variación column, a narrow right-aligned column with an SVG triangle and a signed delta against the row's reference (stock vs reorder level, waiting time, refunded vs gross).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
