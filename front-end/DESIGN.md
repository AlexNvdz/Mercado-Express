---
name: MercadoExpress
description: Staff panel set like the daily wholesale price bulletin; the storefront keeps its fresh-market look on the same tokens.
colors:
  g0: "#f7faf6"
  g1: "#f3f8f2"
  g2: "#e6efe6"
  g3: "#d3e2d5"
  g4: "#b5cbb9"
  g5: "#8ea996"
  g6: "#6c8677"
  g7: "#4b6858"
  g8: "#2f4f3f"
  g9: "#21503b"
  g10: "#17382a"
  paper: "#ffffff"
  volt: "#2e7d50"
  volt-deep: "#22623e"
  volt-soft: "#e2f1e5"
  signal: "#c8e46e"
  signal-deep: "#b2d04c"
  signal-soft: "#f2f9dc"
  rose: "#c8364a"
  rose-soft: "#fbe9ec"
  amber: "#9a6200"
  amber-soft: "#fdf1d6"
  sky: "#2a6a8f"
  sky-soft: "#e3f0f6"
  violet: "#5d559c"
  violet-soft: "#ecebf7"
  leaf: "#2f9a5a"
  leaf-soft: "#e1f3e6"
  line: "#dae8dc"
  line-2: "#c2d7c6"
  paper-2: "#f6faf5"
typography:
  display:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 750
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1.85rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  title:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  button:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1
  label:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.08em"
    fontVariation: "'wdth' 72"
  caption:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  variation:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 650
    fontFeature: "tnum"
rounded:
  sheet: "0px"
  chip: "3px"
  tight: "4px"
  control: "6px"
  r-sm: "8px"
  r-md: "14px"
  r-lg: "22px"
  r-pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  gutter: "28px"
  gutter-phone: "16px"
components:
  button-primary:
    backgroundColor: "{colors.volt}"
    textColor: "{colors.paper}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.volt-deep}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
    height: "38px"
  button-secondary-hover:
    textColor: "{colors.volt-deep}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.volt-deep}"
    rounded: "{rounded.control}"
  button-ghost-hover:
    backgroundColor: "{colors.volt-soft}"
  button-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.rose}"
    rounded: "{rounded.control}"
  button-danger-hover:
    backgroundColor: "{colors.rose}"
    textColor: "{colors.paper}"
  button-small:
    padding: "5px 12px"
    height: "32px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
    height: "38px"
  input-inline:
    rounded: "{rounded.tight}"
    padding: "4px 8px"
    height: "32px"
  global-search:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    rounded: "{rounded.control}"
    height: "38px"
  rail:
    backgroundColor: "{colors.g10}"
    textColor: "{colors.g3}"
    width: "232px"
  rail-link:
    textColor: "{colors.g3}"
    typography: "{typography.body}"
    padding: "9px 20px"
  rail-link-current:
    backgroundColor: "{colors.g9}"
    textColor: "{colors.paper}"
  topbar:
    backgroundColor: "{colors.paper}"
    height: "60px"
    padding: "0 28px"
  sheet:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.sheet}"
    padding: "14px 16px"
  sheet-head:
    typography: "{typography.title}"
    padding: "12px 16px"
  figure:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    typography: "{typography.headline}"
    padding: "14px 18px"
  ledger-head:
    textColor: "{colors.g7}"
    typography: "{typography.label}"
    padding: "8px 12px"
  ledger-cell:
    textColor: "{colors.g10}"
    typography: "{typography.body}"
    padding: "8px 12px"
  ledger-band:
    backgroundColor: "{colors.g10}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    padding: "6px 12px"
  variation-up:
    textColor: "{colors.volt}"
    typography: "{typography.variation}"
  variation-down:
    textColor: "{colors.rose}"
    typography: "{typography.variation}"
  variation-warn:
    textColor: "{colors.amber}"
    typography: "{typography.variation}"
  variation-flat:
    textColor: "{colors.g7}"
    typography: "{typography.variation}"
  chip:
    backgroundColor: "{colors.g2}"
    textColor: "{colors.g8}"
    rounded: "{rounded.chip}"
    padding: "1px 7px"
  chip-off:
    backgroundColor: "{colors.rose-soft}"
    textColor: "{colors.rose}"
  status-pending:
    backgroundColor: "{colors.amber-soft}"
    textColor: "{colors.amber}"
    rounded: "{rounded.chip}"
    padding: "2px 8px 2px 7px"
  status-paid:
    backgroundColor: "{colors.sky-soft}"
    textColor: "{colors.sky}"
  status-shipped:
    backgroundColor: "{colors.violet-soft}"
    textColor: "{colors.violet}"
  status-delivered:
    backgroundColor: "{colors.leaf-soft}"
    textColor: "#1f6b3e"
  status-cancelled:
    backgroundColor: "{colors.rose-soft}"
    textColor: "{colors.rose}"
  filter-tab:
    textColor: "{colors.g7}"
    padding: "9px 14px"
  filter-tab-current:
    backgroundColor: "{colors.g10}"
    textColor: "{colors.paper}"
  pagination-page:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    rounded: "{rounded.tight}"
    size: "32px"
  pagination-page-current:
    backgroundColor: "{colors.g10}"
    textColor: "{colors.paper}"
  share-track:
    backgroundColor: "{colors.g2}"
    height: "6px"
  share-fill:
    backgroundColor: "{colors.volt}"
    height: "6px"
---

# Design System: MercadoExpress

## Overview

**Creative North Star: "The Price Bulletin" (Boletín de precios)**

The staff panel (`/panel/` and `/catalogo/admin/`) reads like the daily wholesale price bulletin printed for a Colombian food market: white sheets ruled in 1px hairlines, rows grouped under solid forest bands, tabular figures in every column, and each key figure printed beside its variation against a reference. The density is deliberate. Staff work through tens of thousands of orders, customers and SKUs, so rows sit on 8px of padding, structural labels are small condensed caps, and nothing on the page is ornament. A forest rail on the left and a white bar holding one global search frame every page.

The colour is flat and committed. An eleven-step green ramp supplies every neutral, the action green marks what can be clicked, lime marks what is current, and rose, amber, sky, violet and leaf speak only for state. Depth comes from hairlines and solid fills, never from shadows or gradients. Sheets are square; controls take small 3-6px corners. The panel refuses the usual admin template of floating metric cards above one generic table.

The storefront keeps its earlier "fresh market" look on the same token file (`static/css/tokens.css`): Bricolage Grotesque for display type and prices, Figtree for 15px body text, rounder corners (`r-sm`, `r-md`, `r-lg`, `r-pill`), the soft `--lift` shadows on hover cards and menus, and the striped awning under the header as its one decorative flourish. The panel scopes its own world under the `panel-app` body class and restyles the shared components (`static/css/components/`) in `static/css/panel/`. The user rejected the "mercado campesino" storefront trial (slate green, kraft-paper tags, scalable section index, animated hero) on 2026-10-22; it stays out of both worlds.

**Key Characteristics:**
- Ruled sheets, not cards: a 1px g3 hairline around and between modules, g2 inside them, square corners.
- One green ramp (g0-g10) for every neutral; volt for actions, lime for the current item.
- Archivo throughout: normal width for reading, condensed caps for structure, tabular figures everywhere.
- Every key figure carries a signed variation against a stated reference.
- The same task works on a phone: ledgers fold into label/value rows and no page scrolls sideways.

## Colors

The pinned MercadoExpress greens, stretched into a fixed ramp, with four state hues held in reserve.

### Primary
- **Garden Action Green** (`volt`, #2e7d50): every primary button, the focus outline, the caret, the share-bar fill, and the "up" variation marker. If a staff member can click it to act, it is this green.
- **Deep Garden Green** (`volt-deep`, #22623e): primary button hover, links, sheet links ("Ver todos"), hover text on secondary buttons and crumbs.
- **Mint Wash** (`volt-soft`, #e2f1e5): the 3px focus ring on fields, the ghost-button hover fill, the soft outline on the focused global search.

### Secondary
- **Market Lime** (`signal`, #c8e46e): the brand mark tile in the rail, the 8px square beside the current rail link, the count and "Ver todos" link inside a forest group band, and text selection. `signal-deep` and `signal-soft` belong to the storefront (its lime button and highlight washes).

### Neutral
- **Forest Ink** (`g10`, #17382a): all body text (it is also `--ink` and `--text`), the rail, group bands, the current filter tab and page number, the 2px rule over a grand total.
- **Rail Hover Forest** (`g9`, #21503b): hover and current fill of rail links (also `--ink-2`).
- **Field Label Green** (`g8`, #2f4f3f): form labels, plain chip text, the rail's internal dividers.
- **Moss Grey** (`g7`, #4b6858): secondary text: column heads, figure labels and notes, sheet notes, crumbs, page-head meta, fact labels, the flat variation marker (also `--text-2`).
- **Sage Grey** (`g6`, #6c8677): decorative marks only: the transition chevron, the pagination ellipsis (also `--text-3`).
- **Lichen** (`g5`, #8ea996): rail group names and rail counts, on forest only.
- **Control Border Sage** (`g4`, #b5cbb9): borders of inputs, selects, the global search and secondary buttons; rail footer links.
- **Hairline Sage** (`g3`, #d3e2d5): the structural hairline around sheets, the figure strip, the filter bar and the top bar; pagination tile borders; rail link text.
- **Inner Rule Mint** (`g2`, #e6efe6): rules inside a sheet (row dividers, fact and total rows, the variation column's left rule), plain chip fill, share-bar track.
- **Mint Canvas** (`g1`, #f3f8f2): the workspace background behind the sheets (also `--canvas`).
- **Row Hover Mist** (`g0`, #f7faf6): ledger row hover, filter tab hover.
- **Sheet White** (`paper`, #ffffff): sheets, the figure strip, the top bar, fields, secondary buttons.
- `line`, `line-2` and `paper-2` are the storefront's neutrals. They reach the panel only through the disabled button state, the one shared component not restyled for it; `.form-field` borders, the confirmation dialog and toasts take `g3`/`g4` hairlines in `panel/records.css`.

### State (status only)
- **Wait Amber** (`amber` / `amber-soft`): pending orders, the warning variation (waiting 24 h or more, unpaid orders behind the queue), `chip--warn`.
- **Paid Sky** (`sky` / `sky-soft`): paid and preparing orders.
- **Transit Violet** (`violet` / `violet-soft`): shipped and in-transit.
- **Delivered Leaf** (`leaf` / `leaf-soft`): delivered and completed, with text darkened to #1f6b3e for contrast; the success toast dot.
- **Alert Rose** (`rose` / `rose-soft`): cancelled, refunded, failed and returned; the "down" variation; "Oculto", "Inactivo" and "Agotado" chips; form errors; danger buttons. On the forest rail the low-stock count uses a pale rose (#f2b8c0).

### Named Rules
**The Ramp-Only Rule.** Every neutral in the panel comes from g0-g10: text, hairlines, row hover, chip fills, the rail. A new tone is taken from the ramp, not mixed. g6 and lighter fail 4.5:1 on white, so they never carry text; body copy is g10 and secondary copy g7.

**The Lime Marks Now Rule.** Lime marks the current or selected thing: the brand mark, the square beside the active rail link, the count inside a group band, selected text. In the panel it never fills a button or a surface.

**The State-Only Rule.** Rose, amber, sky, violet and leaf appear only as state: status chips, variation markers, the low-stock count, errors. They never decorate a section, a heading or a figure that is not reporting a state.

## Typography

**Display Font:** Archivo (with Segoe UI, system-ui, sans-serif)
**Body Font:** Archivo (same family)
**Label Font:** Archivo at the condensed width (`wdth` 72), uppercase

Archivo is loaded as a variable font (width 62-125, weight 400-800) only on panel pages. The panel uses the in-between weights: 550 for fact values, 650 for row codes, variations and current navigation, 750 for page titles and the grand total.

**Character:** One grotesque in two widths, the way a bulletin sets its prices in a plain face and its column heads in tight caps. Nothing is set for display flair; the figures carry the page.

### Hierarchy
- **Display** (750, 1.75rem, 1.15): the page title in the page head, including a record's code on its own page (order number). 1.45rem under 480px.
- **Headline** (700, 1.85rem, 1.1, -0.02em): figure values in the figure strip and nowhere else. 1.5rem under 700px. The grand total of an order uses 1.35rem at 750.
- **Title** (700, 1rem): sheet titles.
- **Body** (400, 14px, 1.45): every cell, field, list and paragraph. Row codes (order number, SKU) at 650; the sub-line under a cell (customer email, product name under a SKU) at 12.5px in g7.
- **Button** (600, 14px; 13px on small buttons).
- **Label** (600, 11px, 0.08em, uppercase, `wdth` 72): ledger column heads, group bands (tracked wider, 0.12em), figure labels, rail group names.
- **Caption** (400, 13px): page-head meta, sheet notes and footers, crumbs, filter labels, the top bar's date and role.
- **Variation** (650, 12.5px): the variation marker's signed figure.

### Named Rules
**The Condensed Caps Rule.** Condensed caps label structure: column heads, group bands, figure labels, rail group names. They never set a heading, a sentence or a button, and never sit above a page title.

**The Tabular Rule.** The whole panel sets `tabular-nums`. Numeric columns are right-aligned so digits stack, and signed variations use a real minus sign (−), not a hyphen.

## Layout

The panel body is a two-column grid: a 232px forest rail and a fluid column holding a sticky 60px white top bar and the workspace (padding 22px 28px 64px, on the g1 canvas). The rail is sticky at full viewport height, with the brand, the grouped navigation (Operación, Catálogo) with live counts, and a footer pushed to the bottom. The top bar holds the global search (up to 620px wide, `/` shortcut hint) and the date and role at the right.

Each page opens with a page head: optional crumbs, then title, a status chip or meta line, and actions pushed to the right on one row. Below it, the dashboard sets one figure strip (auto-fit columns, minimum 180px, the lead figure spanning two) and then sheets in a grid: 1.55fr / 1fr on the dashboard, even halves where two lists compare, or content plus a 340px aside on record pages (order, product form). Sheets in a column stack inside a grid with a 20px gap. Inside a sheet the rhythm is tight: head 12px 16px, body 14px 16px, ledger cells 8px 12px, action rows 8px apart. List pages put a filter bar and, for orders, a strip of status tabs above a single full-width ledger, with pagination joined to its bottom edge.

Responsive behaviour, measured from the build:
- **≤1100px:** sheet grids collapse to one column; the lead figure stops spanning two.
- **≤1024px:** the rail becomes a forest band across the top with every section visible at once in a three-column grid (no hidden menu); counts and group names hide; the top bar stops sticking and wraps; the workspace pads 18px 16px 48px.
- **≤700px:** the figure strip becomes two columns with the lead figure full width; ledgers fold into rows (see Components); buttons, page numbers, inline inputs, selects and tabs grow to 44px tall.
- **≤480px:** the rail grid drops to two columns, page-head actions take the full width, the `/` hint hides.

### Named Rules
**The No Sideways Page Rule.** No panel page scrolls horizontally on a phone. Ledgers fold into label/value rows instead of scrolling, so every ledger cell except the lead one carries a `data-label`.

**The Joined Module Rule.** Related figures and controls share one container divided by hairlines: the figure strip, the status tabs, the pagination bar under its ledger. Modules are never separated by air and floated as cards.

## Elevation & Depth

The panel is flat. Depth is the g1 canvas behind white sheets, a 1px g3 hairline around and between modules, a 1px g2 rule inside them, and solid g10 fills for the rail, group bands, the current tab and page, plus a 2px g10 rule above a grand total. Hover changes fill, not height: a ledger row tints to g0 and a rail link fills g9. Panel buttons explicitly drop any shadow and any press offset.

The tokens file keeps two shadows for the storefront: `--lift` (`0 12px 28px -16px rgba(23, 56, 42, 0.28)`, product cards on hover) and `--lift-lg` (`0 26px 50px -24px rgba(23, 56, 42, 0.38)`, menus and the hero ticket). The panel uses neither: `panel/records.css` strips them from the shared confirmation dialog and toasts, which take a `g3` hairline and 6px corners instead. They are not a precedent for panel surfaces.

### Named Rules
**The Flat Sheet Rule.** Panel surfaces are flat at rest and on hover. A module separates from its neighbour by a hairline, never by a shadow or a gradient.

## Shapes

Sheets, the figure strip, the filter bar, the status tabs and group bands are square. Controls take small corners: 6px on buttons, inputs, selects, the global search and the brand mark tile; 4px on the smaller pieces (page numbers, inline cell inputs, thumbnails, image tiles, the keyboard hint, icon buttons); 3px on chips and status chips. The status dot inside a chip is a 6px square with a 1px corner, and the current-link marker in the rail is an 8px square with 2px corners, so even the round marks of the storefront turn square here.

Markers are drawn shapes. The variation triangle is an 8x7px `clip-path` in `currentColor`, pointing up or down; the "from → to" mark in the status history is a 7x9px chevron in g6. Icons are inline SVG at 16px with 2-2.2px strokes (search, bag mark, close).

### Named Rules
**The Drawn Marker Rule.** Triangles and chevrons are drawn with CSS `clip-path` in `currentColor`, never typed as glyphs (▲ ▼ →) or pulled from an icon font.

## Components

Panel components are standard web controls in the bulletin's squared, ruled language. Shared components keep their storefront defaults in `static/css/components/`; the panel overrides them under `.panel-app` in `static/css/panel/records.css` and `sheets.css`, which load after them (`templates/adminpanel/_layout.html`). New panel styling goes there, scoped the same way.

### Buttons
- **Shape:** gently squared (6px corners), 38px tall, 8px 16px padding, 14px at 600.
- **Primary:** action green fill with white text; hover deepens to `volt-deep`.
- **Secondary:** white with a g4 border and g10 text; hover turns the border volt and the text `volt-deep`. Used for filters, inline "Ajustar"/"Guardar", "Ver pedidos".
- **Ghost:** no fill, `volt-deep` text, mint-wash fill on hover. Used for "Cancelar" and "Limpiar".
- **Danger:** white with rose text and a pale rose border, filling rose on hover. Always behind a `data-confirm` dialog with `data-confirm-tone="danger"`.
- **Small:** 32px tall, 5px 12px, 13px. All buttons grow to 44px under 700px.
- **No lift, no press:** panel buttons have no shadow and no `translateY` on press. Disabled buttons take the `line` fill and g6 text.

### Chips
- **Status chip:** 3px corners, 2px 8px padding, 12px at 600, a squared 6px dot in the text colour. One hue family per stage (see Colors, State). The label is always the Spanish one from the `status_labels` filters; the English value stays in the class.
- **Plain chip:** g2 fill, g8 text, 1px 7px padding ("Publicado"). `chip--off` in rose for "Oculto", "Inactivo", "Agotado"; `chip--warn` in amber.

### Sheets
- **Corner Style:** square.
- **Background:** white on the g1 canvas, 1px g3 border.
- **Shadow Strategy:** none (see The Flat Sheet Rule).
- **Head:** 12px 16px, title at 1rem/700 on the left, a note or "Ver ..." link on the right, g3 hairline below.
- **Body / Foot:** body 14px 16px; foot 10px 16px under a g2 rule, 13px in g7.
- **Empty state:** centred inside the sheet, 28px padding, 1.05rem heading, g7 line, optional button. No illustration.

### Figure strip
One white strip of figures joined by g3 hairlines, never separate cards. Each figure: condensed-caps label in g7, the value at headline size in g10, and a 12.5px note in g7 that carries a variation marker. The lead figure (net revenue) spans two columns.

### Inputs / Fields
- **Style:** white, 1px g4 border, 6px corners, 38px tall (36px in the filter bar), Archivo inherited.
- **Labels:** 13px at 600 in g8, above the field.
- **Focus:** border turns volt with a 3px `volt-soft` ring; the global search shows a volt border and a 2px `volt-soft` outline. Every other focusable element gets a 2px volt outline at 2px offset.
- **Inline cell forms:** 32px tall, 4px corners, numbers right-aligned, quantity fields 112px and reorder fields 76px, so a row can be corrected in place.
- **Error:** 13px rose text under the field.
- **Filter bar:** a white hairline-bordered bar, 12px padding, search field growing first (minimum 280px), then selects and dates, then "Filtrar"/"Buscar" and "Limpiar".

### Navigation
- **Rail:** forest (g10), links g3 at 500 with 9px 20px padding, counts at 12px in g5 on the right. Hover and current fill g9 with white text; the current link turns 650 and gains the lime square. Group names in condensed caps, g5. Footer links in g4 ("Ver tienda como cliente", "Cerrar sesión"). On tablets and phones it becomes a forest band with all links in a grid.
- **Global search:** one field in the top bar, magnifier icon, placeholder "Buscar pedido, cliente o SKU", `/` keyboard hint.
- **Status tabs:** a joined white strip, square, links divided by g2 rules, g7 at 500; the current tab fills g10 with white text at 650.
- **Pagination:** a white bar joined to the bottom of the ledger above it (no top border), with Anterior/Siguiente, numbered 32px tiles with 4px corners and g3 borders, the current page filled g10, and a "Página N de M · Ir a" jump field.
- **Crumbs:** 13px g7 text with a `/` separator, above record titles.

### Ledger (signature)
The bulletin table. Column heads in condensed caps, g7, over a g3 hairline; rows divided by g2 rules, 8px 12px cells, g0 on hover. **Every row leads with its code** (order number, SKU) at 650, linked to the record. Group bands are full-width g10 rows in condensed caps with a lime count and a lime "Ver todos" link on the right, used to group orders by stage. On phones the header hides and each row becomes a block: the lead cell is the row heading, numeric cells pair two per line with their `data-label`, text cells take the full width.

### Variation column (signature)
The narrow right-aligned column at the end of a ledger (`vcol`, set off by a g2 rule) and the note line of each figure. A marker is a drawn triangle plus a signed figure at 12.5px/650 against a named reference:
- **Up** (volt): above the reference, for example stock above its reorder level.
- **Down** (rose): below it, or a loss: stock under reorder level, refunds against gross revenue.
- **Warn** (amber, up triangle): time that has run long: an order waiting 24 h or more since its last change, unpaid orders behind the queue.
- **Flat** (g7, no triangle): at the reference, or an elapsed time that needs no alarm.
References in use: stock vs reorder level, time since the last status change ("Espera"), time between history entries ("Tras"), refunds vs gross revenue.

### Totals and facts
- **Totals:** ruled rows (g2) of label and amount; the grand total sits under a 2px g10 rule at 1.35rem/750.
- **Facts:** a two-column label/value list, labels in g7, values at 550 right-aligned, g2 rules between rows.
- **Share bar:** a 6px g2 track with a volt fill and the percentage on the right, for the order-status distribution.

## Do's and Don'ts

### Do:
- **Do** take every new neutral from `--g0`..`--g10`; text on white is g7 or darker.
- **Do** print each key figure beside its variation against a named reference, in a right-aligned variation column or a figure note.
- **Do** join related figures, tabs and pagination into one hairline-divided container.
- **Do** lead every ledger row with the record's code, linked, and give every other cell a `data-label`.
- **Do** keep sheets square with a 1px g3 border, and controls at 6px (4px for small pieces, 3px for chips).
- **Do** grow every panel control to 44px under 700px.
- **Do** scope panel styling under `.panel-app` in `static/css/panel/`, loaded after the shared components.

### Don't:
- **Don't** float metric cards separated by air above one generic table.
- **Don't** add shadows or gradients to panel surfaces, or a press offset to panel buttons.
- **Don't** fill a button or a surface with lime in the panel.
- **Don't** use rose, amber, sky, violet or leaf except to report a state.
- **Don't** set headings, sentences or buttons in condensed caps, or put a caps line above a page title.
- **Don't** type arrows or triangles as glyphs; draw them with `clip-path`.
- **Don't** let a ledger scroll the page sideways on a phone.
- **Don't** bring the storefront's Bricolage Grotesque, Figtree, 14px and 22px corners or lift shadows into the panel.
- **Don't** reuse the rejected "mercado campesino" trial (slate green, kraft-paper tags, scalable section index, animated hero).
