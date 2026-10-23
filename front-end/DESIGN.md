---
name: MercadoExpress
description: Two worlds on one token file. The staff panel is set like the daily wholesale price bulletin. The storefront sits under a striped market-canvas awning and shows only real stock.
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
  canvas-stripe: "#e9f4ea"
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
  store-hero:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(2.4rem, 1.6rem + 3.6vw, 4.3rem)"
    fontWeight: 800
    lineHeight: 0.97
    letterSpacing: "-0.03em"
    fontVariation: "'wdth' 80"
  store-title:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(1.8rem, 1.4rem + 1.6vw, 2.4rem)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 82"
  store-heading:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(1.6rem, 1.2rem + 1.4vw, 2.2rem)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  store-shelf:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(1.15rem, 1rem + 0.6vw, 1.5rem)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 85"
  store-price:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  store-lead:
    fontFamily: "Figtree, Segoe UI, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(1rem, 0.95rem + 0.3vw, 1.15rem)"
    fontWeight: 400
    lineHeight: 1.55
  store-body:
    fontFamily: "Figtree, Segoe UI, system-ui, -apple-system, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  store-chip:
    fontFamily: "Figtree, Segoe UI, system-ui, -apple-system, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
  store-button:
    fontFamily: "Figtree, Segoe UI, system-ui, -apple-system, sans-serif"
    fontSize: "0.92rem"
    fontWeight: 600
    lineHeight: 1
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
  store-button:
    backgroundColor: "{colors.volt}"
    textColor: "{colors.paper}"
    typography: "{typography.store-button}"
    rounded: "{rounded.r-sm}"
    padding: "0 18px"
    height: "42px"
  store-button-hover:
    backgroundColor: "{colors.volt-deep}"
  store-button-soft:
    backgroundColor: "{colors.volt-soft}"
    textColor: "{colors.volt-deep}"
    rounded: "{rounded.r-sm}"
    padding: "0 12px"
    height: "34px"
  header-search:
    backgroundColor: "{colors.g1}"
    textColor: "{colors.g10}"
    rounded: "{rounded.r-pill}"
    height: "46px"
  header-search-focus:
    backgroundColor: "{colors.paper}"
  subnav:
    backgroundColor: "{colors.volt-soft}"
    textColor: "{colors.g9}"
    height: "44px"
  awning-hem:
    backgroundColor: "{colors.volt}"
    height: "9px"
  category-menu:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.r-md}"
    padding: "8px"
    width: "320px"
  hero-search:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    rounded: "16px"
    padding: "6px"
  hero-search-button:
    backgroundColor: "{colors.g10}"
    textColor: "{colors.paper}"
    rounded: "{rounded.r-sm}"
    height: "46px"
  product-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    rounded: "{rounded.r-md}"
    padding: "14px 16px 16px"
  product-card-media:
    backgroundColor: "{colors.paper-2}"
    padding: "14px"
  product-card-price:
    textColor: "{colors.g10}"
    typography: "{typography.store-price}"
  stock-line:
    textColor: "{colors.g7}"
  stock-line-out:
    textColor: "{colors.rose}"
  count-chip:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.g10}"
    typography: "{typography.store-chip}"
    rounded: "{rounded.r-pill}"
    padding: "2px 9px"
  category-row:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.g10}"
    rounded: "{rounded.r-md}"
    padding: "10px 16px"
    height: "64px"
  catalog-filter:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.r-md}"
    padding: "16px 10px"
    width: "240px"
  catalog-filter-link:
    textColor: "{colors.g7}"
    rounded: "{rounded.r-sm}"
    padding: "9px 10px"
  catalog-filter-link-current:
    backgroundColor: "{colors.volt-soft}"
    textColor: "{colors.volt-deep}"
  flow-card:
    backgroundColor: "rgba(255, 255, 255, 0.94)"
    textColor: "{colors.g10}"
    rounded: "{rounded.r-lg}"
    padding: "18px"
    width: "440px"
  flow-tag:
    backgroundColor: "{colors.volt-soft}"
    textColor: "{colors.g7}"
    rounded: "{rounded.r-pill}"
    padding: "2px 9px"
  flow-track-segment:
    backgroundColor: "{colors.volt-soft}"
    rounded: "{rounded.r-pill}"
    height: "6px"
  flow-chip-paid:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.g10}"
    rounded: "{rounded.r-pill}"
    padding: "8px 13px"
  flow-chip-preparing:
    backgroundColor: "{colors.sky-soft}"
    textColor: "{colors.sky}"
    rounded: "{rounded.r-pill}"
    padding: "6px 12px"
  flow-road:
    backgroundColor: "{colors.violet-soft}"
    rounded: "{rounded.r-pill}"
    height: "32px"
  flow-truck:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.paper}"
    size: "32px"
---

# Design System: MercadoExpress

## Overview

**Creative North Star: "The Price Bulletin" (Boletín de precios)**

The staff panel (`/panel/` and `/catalogo/admin/`) reads like the daily wholesale price bulletin printed for a Colombian food market: white sheets ruled in 1px hairlines, rows grouped under solid forest bands, tabular figures in every column, and each key figure printed beside its variation against a reference. The density is deliberate. Staff work through tens of thousands of orders, customers and SKUs, so rows sit on 8px of padding, structural labels are small condensed caps, and nothing on the page is ornament. A forest rail on the left and a white bar holding one global search frame every page.

The colour is flat and committed. An eleven-step green ramp supplies every neutral, the action green marks what can be clicked, lime marks what is current, and rose, amber, sky, violet and leaf speak only for state. Depth comes from hairlines and solid fills, never from shadows or gradients. Sheets are square; controls take small 3-6px corners. The panel refuses the usual admin template of floating metric cards above one generic table.

The panel scopes its own world under the `panel-app` body class and restyles the shared components (`static/css/components/`) in `static/css/panel/`. The storefront is a second world on the same token file (`static/css/tokens.css`).

**Storefront North Star: "The Market Canvas" (La lona del mercado)**

The storefront sits under a market stall's canvas. A scalloped hem of action green and lime stripes runs under the header on every customer page, and the home hero stands on wide stripes of pale canvas. A few real product photos drift slowly over those stripes, and a light card plays an example order through its five real states, from cart to delivered. Everything below is honest stock: square white product cards that state the units in the warehouse, a lime chip counting the products of every category, and only the categories and products that exist today. Bricolage Grotesque, narrowed and heavy, sets the headings and prices; Figtree sets the text at 15px. Corners are round (8, 14 and 22px, and pills), and a soft green-tinted shadow lifts a card on hover.

The home, the product catalog and the category index carry this system, approved on 2026-10-23. Pages not yet restyled (cart, checkout, account, order detail) still wear the earlier "fresh market" styling on the same tokens. The user rejected the "mercado campesino" storefront trial (slate green, kraft-paper tags, scalable section index, its animated hero) on 2026-10-22; it stays out of both worlds. The motion the home does have, the example-order loop and the drifting photos, is what the user asked for afterwards.

**Key Characteristics:**
- Ruled sheets, not cards: a 1px g3 hairline around and between modules, g2 inside them, square corners.
- One green ramp (g0-g10) for every neutral; volt for actions, lime for the current item.
- Archivo throughout: normal width for reading, condensed caps for structure, tabular figures everywhere.
- Every key figure carries a signed variation against a stated reference.
- The same task works on a phone: ledgers fold into label/value rows and no page scrolls sideways.
- Storefront: a scalloped volt and lime awning hem under the header, and market-canvas stripes behind the home hero.
- Storefront: square white product cards that state their stock, and a lime chip that counts every category.
- Storefront: an example order cycles its five real states, each in its status hue, and stills to a list under reduced motion.

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

### Storefront
The storefront reads the same values through its own aliases: `--ink` (g10) for text and the ink-filled hero search button, `--ink-2` (g9) for sub-navigation links, `--text-2` (g7) for secondary text, product names and the stock line, `--text-3` (g6) for placeholders, `--canvas` (g1) as the page background, `line` and `line-2` for card and row borders, `paper-2` for the product photo well.
- **Market Canvas Stripe** (`canvas-stripe`, #e9f4ea): alternates with the mint canvas in 72px vertical bands behind the home hero. It is the `--canvas-stripe` custom property in `tokens.css`.
- **Awning stripes:** the hem under the header alternates `volt` and `signal` in 24px stripes below the `volt-soft` sub-navigation strip.
- **Lime** (`signal`): count chips ("3 productos"), the cart and wishlist count badges, and the "Pago aprobado" chip in the example order, always with ink text. `signal-soft` is the focus halo of the hero search.
- **Order states in the example order:** lime for the approved payment, sky for "En preparación", violet for "Enviado" and the truck's road, action green for the cart step and the delivered badge. Out of stock is rose ("Agotado").

### Named Rules
**The Ramp-Only Rule.** Every neutral in the panel comes from g0-g10: text, hairlines, row hover, chip fills, the rail. A new tone is taken from the ramp, not mixed. g6 and lighter fail 4.5:1 on white, so they never carry text; body copy is g10 and secondary copy g7.

**The Lime Marks Now Rule.** Lime marks the current or selected thing: the brand mark, the square beside the active rail link, the count inside a group band, selected text. In the panel it never fills a button or a surface.

**The State-Only Rule.** Rose, amber, sky, violet and leaf appear only as state: status chips, variation markers, the low-stock count, errors. They never decorate a section, a heading or a figure that is not reporting a state.

**The Lime Counts Rule.** In the storefront lime fills small things that count or confirm: count chips, count badges, the payment-approved chip, and half of the awning's stripes. It always carries ink text and never fills a page section, a card or the primary action, which stays action green.

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

### Storefront
**Display Font:** Bricolage Grotesque (with Segoe UI, system-ui, sans-serif), variable: optical size 12-96, width 75-100, weight 600-800, loaded from Google Fonts in `base.html`.
**Body Font:** Figtree (with Segoe UI, system-ui, -apple-system, sans-serif), weights 400-700.

**Character:** A lively grotesque narrowed for the big words, the way a stall paints its name across the canvas, beside a plain, friendly sans for everything that is read.

- **Hero** (`store-hero`: 800, clamp 2.4-4.3rem, 0.97, -0.03em, width 80, at most 11ch): the home's H1 only.
- **Page title** (`store-title`: 800, clamp 1.8-2.4rem, width 82): "Todas las categorías". Other page H1s keep the default heading (`store-heading`: 700, clamp 1.6-2.2rem); the catalog's title uses the 1.3-1.7rem section title.
- **Category name** (`store-shelf`: 800, width 85): shelf heads on the home (clamp 1.15-1.5rem) and category rows (1.12rem).
- **Card title:** the example-order card's "Así va un pedido" at 750, 1.15rem.
- **Price** (`store-price`: 600, 1.35rem, 1.1): product card prices, at normal width. The example order's total uses 800 at 1.6rem.
- **Lead** (`store-lead`: Figtree 400, clamp 1-1.15rem, at most 40ch): `--text-2`, opening with the product count in bold ink.
- **Body** (`store-body`: Figtree 400, 15px, 1.55). Product names at 0.92rem/1.35, clamped to two lines in `--text-2`; the stock line at 0.8rem.
- **Chip** (`store-chip`: Figtree 700, 0.8rem, no wrap): count chips.

**The Narrowed Heading Rule.** Only headings shout: the hero, page titles and category names set Bricolage at 800 on a narrowed width (80-85) with tight tracking. Prices stay at 600 and normal width, and running text is always Figtree.

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

### Storefront
The storefront body is a full-height flex column whose `<main>` takes the slack, so the footer stays at the bottom of short pages. Content sits in a 1240px container with a `clamp(16px, 4vw, 28px)` gutter; the home's `<main>` drops its padding so the hero runs full bleed.

- **Header:** sticky. A white row (brand, the search up to 640px, account links, wishlist and cart), then the 44px mint sub-navigation (Categorías menu, shortcuts, a right-aligned note), then the 9px awning hem. On the home the header search hides, because the hero's search is the page's only search field.
- **Home hero:** a wrapping row on the canvas stripes, padded clamp(26px, 5vw, 56px) above and clamp(30px, 5vw, 60px) below. The copy (title, lead, search up to 560px, two text links) grows from 460px; the example-order card takes 360-440px beside it and drops below the copy on phones. The first thing in the copy is the H1; there is nothing above it.
- **Shelves:** "Por categoría", then one section per category: a head row (category name, count chip, "Ver todo" pushed right) over a product grid. A full-width secondary button "Ver las N categorías" (at most 420px, centred) closes the list when more categories exist than shelves shown.
- **Product grid:** 2 columns, 3 from 700px, 4 from 1100px (5 on the wide grid), gaps clamp(10px, 1.6vw, 16px).
- **Catalog:** a 240px category list beside a fluid column (gap 24px); the list is sticky under the 118px header. The column holds the title and product count, the grid and pagination.
- **Category index:** a single 720px column: title, lead, search, then the category rows 8px apart.

Responsive behaviour, measured from the build:
- **≤1100px:** the grid drops to 3 columns; the second and third floating photos hide.
- **≤900px:** the header search takes its own full-width 44px row, account links fold behind a menu toggle, the sub-navigation note hides and the category menu spans the viewport with 16px insets; the catalog goes to one column and its category list becomes a closed `<details>` above the grid.
- **≤760px:** the remaining floating photo shrinks to 76px and tucks off the right edge; card buttons grow to 44px.
- **<700px:** the grid is 2 columns.

**The Real Shelf Rule.** The storefront shows only what exists: the home lists only categories that have active products, most products first, and inside each only products in stock; the count in the lead and on every chip is the real one. No banner carousel, no wall of category icons, no invented delivery times, reviews or best sellers.

## Elevation & Depth

The panel is flat. Depth is the g1 canvas behind white sheets, a 1px g3 hairline around and between modules, a 1px g2 rule inside them, and solid g10 fills for the rail, group bands, the current tab and page, plus a 2px g10 rule above a grand total. Hover changes fill, not height: a ledger row tints to g0 and a rail link fills g9. Panel buttons explicitly drop any shadow and any press offset.

The storefront lifts softly, with shadows tinted by the forest ink (rgba 23, 56, 42). Cards and rows are flat at rest with a 1px `line` border; a product card lifts on hover, and menus and dialogs lift when open. Two things float at rest, both in the home hero: the example-order card and the drifting product photos. Focus on the two search fields is a 4px halo instead of an outline. The panel uses none of these shadows: `panel/records.css` strips them from the shared confirmation dialog and toasts, which take a `g3` hairline and 6px corners instead. They are not a precedent for panel surfaces.

### Shadow Vocabulary
- **Lift** (`--lift`, `box-shadow: 0 12px 28px -16px rgba(23, 56, 42, 0.28)`): a product card on hover, with a `line-2` border.
- **Lift large** (`--lift-lg`, `box-shadow: 0 26px 50px -24px rgba(23, 56, 42, 0.38)`): the open category menu, the shared confirmation dialog and toasts.
- **Flow card** (`box-shadow: 0 24px 50px -28px rgba(23, 56, 42, 0.55)`): the example-order card, on 94% white over the stripes.
- **Floating photo** (`box-shadow: 0 16px 32px -16px rgba(23, 56, 42, 0.45)`): the hero's drifting photos, inside a 4px white frame.
- **Search halo** (`box-shadow: 0 0 0 4px`): `signal-soft` around the hero search; `volt-soft` with a volt border around the header search.

### Named Rules
**The Flat Sheet Rule.** Panel surfaces are flat at rest and on hover. A module separates from its neighbour by a hairline, never by a shadow or a gradient.

**The Lift On Response Rule.** In the storefront a surface lifts only in response: a product card on hover, a menu or dialog when open. Only the hero's example-order card and floating photos float at rest.

## Shapes

Sheets, the figure strip, the filter bar, the status tabs and group bands are square. Controls take small corners: 6px on buttons, inputs, selects, the global search and the brand mark tile; 4px on the smaller pieces (page numbers, inline cell inputs, thumbnails, image tiles, the keyboard hint, icon buttons); 3px on chips and status chips. The status dot inside a chip is a 6px square with a 1px corner, and the current-link marker in the rail is an 8px square with 2px corners, so even the round marks of the storefront turn square here.

Markers are drawn shapes. The variation triangle is an 8x7px `clip-path` in `currentColor`, pointing up or down; the "from → to" mark in the status history is a 7x9px chevron in g6. Icons are inline SVG at 16px with 2-2.2px strokes (search, bag mark, close).

### Named Rules
**The Drawn Marker Rule.** Triangles and chevrons are drawn with CSS `clip-path` in `currentColor`, never typed as glyphs (▲ ▼ →) or pulled from an icon font.

### Storefront
The storefront is round. Buttons, menu items and category links take 8px (`r-sm`); product cards, category rows, the catalog category list, the menu panel and empty states 14px (`r-md`); the example-order card and the product detail 22px (`r-lg`); the header search, count chips, tags, the flow's track and road, and its status chips are full pills. The hero search and the flow's inner tiles (photo, total) take 16px, the floating photos 20px inside a 4px white frame; icon links, the truck and the delivered badge are circles. Product photos sit in a square (1:1) well, contained with a 14px inset so a square photo is never cropped or stretched. The brand mark is a 36px volt tile with three 11px corners and one 4px corner, a lime bag drawn inside.

The awning is CSS only: below the mint strip a 9px band of 24px volt and lime stripes is masked by a row of radial-gradient half-ellipses (12px by 9px, repeating every 24px) into a scalloped hem. The hero's canvas is a `repeating-linear-gradient` of 72px bands. Icons are inline SVG at 14-22px with 1.8-2.6px round strokes; the phone category list draws its chevron from two borders of a rotated 9px square.

**The Painted Canvas Rule.** The awning hem and the canvas stripes are drawn with gradients and a mask, never an image. The hem appears once per page, under the storefront header; the staff console header drops it.

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

### Storefront components
The storefront's own styling lives in `static/css/storefront/` (`header.css`, `home.css`, `catalog.css`) on top of the shared defaults in `static/css/components/`. Storefront buttons are the shared ones: 42px, 8px corners, Figtree 600 at 0.92rem, volt with a white label (volt-deep on hover), a 1px press offset; the soft variant (volt-soft fill, volt-deep text) adds to the cart, and the secondary one is white with a line border.

### Header and awning (storefront)
- **Top row:** white. The brand (mark plus "MercadoExpress" in Bricolage 700, 1.18rem); the header search (pill, canvas fill, 1px line border, 46px, a round volt submit button; on focus it turns white with a volt border and a 4px volt-soft halo); account links (0.9rem/500 in `--text-2`, "Crear cuenta" as a volt pill); two 42px round icon links (wishlist, cart) with lime count badges ringed in white.
- **Sub-navigation:** the mint strip (volt-soft, 44px) with the Categorías menu, shortcuts (Favoritos, plus Seguir mi pedido and Direcciones when signed in) and the note "Pago al instante y seguimiento de cada envío". The awning hem hangs below it.
- **Phones (≤900px):** the search takes its own row, the account links fold behind a 42px menu toggle into a column, the note hides.

### Category menu
A native `<details>` (app.js closes it on an outside click). The panel is white, up to 320px wide, 14px corners, a line border and `--lift-lg`. It lists "Ver todos los productos" first (600, ruled below), then each category with its product count right-aligned in tabular figures (the current one in volt-soft with volt-deep text), then "Ver todas las categorías" (600, volt-deep, ruled above). Items are 10px 12px with 8px corners and turn volt-soft on hover.

### Hero search
White, 2px ink border, 16px corners, 6px inner padding: a 46px field at 1.05rem ("¿Qué necesitas hoy?") and an ink-filled "Buscar" button. Focus adds a 4px `signal-soft` halo. The category index repeats it with 14px corners and a 44px field.

### Product card
- **Corner Style:** 14px, white, a 1px `line` border, contents clipped.
- **Media:** a square `paper-2` well above a 1px line, the photo contained with a 14px inset; a heart button top-right on a 92% white disc (rose when saved). Without a photo, a drawn bag in `line-2`.
- **Body** (14px 16px 16px, 6px gaps): the price in Bricolage, the name in two clamped lines (its link covers the whole card), the stock line ("49 en bodega" in `--text-2`, or "Agotado" in rose at 600), then a full-width soft "Añadir al carrito" button (34px; 44px under 760px). An inactive or sold-out product shows the same button disabled ("No disponible", "Agotado").
- **Hover:** `--lift`, a `line-2` border, and the photo scales to 1.04 over 0.3s.

### Count chip and category row
- **Count chip:** a lime pill (2px 9px, ink text, Figtree 700 at 0.8rem) reading "N productos", beside each category name on the home and in each category row. The catalog's category list uses a compact one (0 7px, 0.78rem, tabular) pushed right.
- **Category row** ("Todas las categorías"): a 64px white row with 14px corners and a line border: the name in Bricolage 800 at width 85, the count chip, a drawn volt-deep chevron. Hover turns the border volt. A search field above filters the list by name.

### Catalog category list
On desktop a 240px white panel (14px corners, line border, 16px 10px), sticky under the header: the title "Categorías: <current>" in Bricolage 600 at 0.95rem, then "Todas", the first 12 categories with compact count chips, and "Ver las N categorías". Links are 9px 10px with 8px corners, 0.92rem in `--text-2`; hover fills `paper-2`; the current one fills volt-soft with volt-deep text at 600. At 900px and below the same element is a closed `<details>` above the grid, with a 44px summary naming the current category and a drawn chevron; `static/js/modules/catalog-filter.js` opens it on wide screens.

### Example order card (signature)
"Así va un pedido", labelled "Ejemplo" in a volt-soft tag, floats beside the hero copy on 94% white with 22px corners and the flow shadow. Under the head runs a five-segment track (6px pills, 5px apart). The five steps share one grid cell and play in a CSS-only 14s loop, 2.8s each: a step enters from 14px below at 0.98 scale, holds, and leaves 6px upward; its badge pops in (0.5, then 1.12, then 1). The segments fill as the order advances: action green for the cart and the payment, sky for preparation, violet for shipment, action green for delivery.
1. **Agregas al carrito:** a real in-stock product's photo (76px, 16px corners), name, price and units in stock, and a 44px volt add tile.
2. **Pagas:** the total on a canvas tile (Bricolage 800, 1.6rem, "Total · Tarjeta") and a lime "Pago aprobado" chip with a drawn check.
3. **Preparamos:** an example order code, a 36px product thumbnail and a sky "En preparación" chip.
4. **Va en camino:** a tracking number ("Guía"), "Enviado" in violet, and a 32px violet truck that rides a violet-soft road.
5. **Te llega:** a 60px volt circle with a check and "Entregado".

Each step ends with a caption: the numbered step in bold, then one plain line. Under reduced motion the track hides and the five steps read as a static list, in order.

### Floating photos
Up to three real product photos taken from the shelves below, in 96, 76 and 68px tiles with 20px corners and a 4px white frame, at 0.85, 0.7 and 0.6 opacity, tilted between -8° and 9°, drifting 8-12px over 6, 7 and 8s. They are ambient: `aria-hidden`, empty `alt`, no link, no caption. Under reduced motion they stand still.

### Pages not yet restyled
Cart, checkout, account and order detail still use the earlier "fresh market" styling (`sections.css`, `cart-checkout.css`, `account.css`, `auth.css`) on the same tokens, for example stock pills in leaf, amber and rose and checkout steps numbered in volt circles. This is current state, not a pattern for new work: new storefront screens follow the home and catalog above.

## Do's and Don'ts

### Do:
- **Do** take every new neutral from `--g0`..`--g10`; text on white is g7 or darker.
- **Do** print each key figure beside its variation against a named reference, in a right-aligned variation column or a figure note.
- **Do** join related figures, tabs and pagination into one hairline-divided container.
- **Do** lead every ledger row with the record's code, linked, and give every other cell a `data-label`.
- **Do** keep sheets square with a 1px g3 border, and controls at 6px (4px for small pieces, 3px for chips).
- **Do** grow every panel control to 44px under 700px.
- **Do** scope panel styling under `.panel-app` in `static/css/panel/`, loaded after the shared components.
- **Do** keep the scalloped awning hem under the storefront header and the canvas stripes behind the home hero.
- **Do** open the home with the H1 and put the product count in bold at the start of the lead.
- **Do** show only categories that have products, most products first, and on the home only products in stock.
- **Do** use real product photos only: on cards, in the example order, in the floating hero tiles.
- **Do** keep each order state in its status hue wherever the order flow is shown: sky for preparing, violet for shipped.
- **Do** give every storefront animation a reduced-motion state that still shows its content.
- **Do** count with lime pills and ink text.

### Don't:
- **Don't** float metric cards separated by air above one generic table.
- **Don't** add shadows or gradients to panel surfaces, or a press offset to panel buttons.
- **Don't** fill a button or a surface with lime in the panel.
- **Don't** use rose, amber, sky, violet or leaf except to report a state.
- **Don't** set headings, sentences or buttons in condensed caps, or put a caps line above a page title.
- **Don't** type arrows or triangles as glyphs; draw them with `clip-path`.
- **Don't** let a ledger scroll the page sideways on a phone.
- **Don't** bring the storefront's Bricolage Grotesque, Figtree, 14px and 22px corners or lift shadows into the panel.
- **Don't** reuse the rejected "mercado campesino" trial (slate green, kraft-paper tags, scalable section index, its animated hero). The home's example-order loop and drifting photos are the motion the user asked for later.
- **Don't** put an eyebrow, kicker or pill above a storefront H1.
- **Don't** put a banner carousel or a wall of category icons on the home, or invent delivery times, reviews or best sellers.
- **Don't** add a second search field to the home; the hero's search replaces the header's there.
- **Don't** fill a card, a section or the primary action with lime.
- **Don't** extend the earlier "fresh market" styling of the cart, checkout, account and order pages to new screens.
