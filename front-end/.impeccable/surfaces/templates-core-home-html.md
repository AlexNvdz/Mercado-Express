---
version: 1
slug: "templates-core-home-html"
primary_target: "templates/core/home.html"
related_targets: ["templates/catalog","templates/cart","templates/orders"]
---

# Storefront home (/), then the rest of the storefront

Mode: Persuade (home), then Operate for catalog, cart, checkout, account and orders, all in the same world. Audience: visitors and customers in Colombia, phone first. Job: find a product fast, trust the stock, understand how buying works, and add to cart. Constraints: Django templates, vanilla JS, no build step; Spanish copy; pinned greens (PRODUCT.md); only categories with active products are shown (`GET /categories?with_products=true&sort=products`); no invented claims (no delivery times, reviews or "best sellers"); real product photos only. Pinned by the user across three rounds: keep the market-tent canvas awning ("la lona como de carpa de mercado"), keep an animated space that shows how buying works (the order process step by step), and use the roll's greens.

Chosen direction: "La cubeta" won the third roll (seed below), then the user steered the approved prototype away from the trays (2026-10-23): plain square product cards so square photos are not distorted, an animated card that walks through the real order flow, and an ambient (not clean) hero background. The approved prototype is the Claude Design canvas https://claude.ai/artifact/VKLZ4fs2SCxybkZfy31Xiy (Inicio celular, Inicio escritorio, Todas las categorías). Memorable moment: a light floating card plays a real order from cart to delivered (ORD number, payment approved, guía, delivered) over the market-canvas stripes.

Process: approved prototype first, code second (done). Nothing reaches main before the 2026-10-26 sustentación without the user's OK and an end-to-end check of login, cart, checkout and order detail.

## Direction contract

THESIS: The home proves the store is real: what you see is in stock, and a live example order walks from cart to delivered. It refuses the category default of a banner carousel over a wall of 80 category icons.

OWN-WORLD: Pinned greens: mint canvas #f3f8f2 with wide market-canvas stripes (#e9f4ea) behind the hero, the scalloped volt/lime awning under the header, white square product cards (16-18px corners, a 1px g3 base line), forest ink #17382a, action green #2e7d50, lime #c8e46e for counts and the payment-approved chip; order states keep their status hues (sky preparing, violet shipped). Bricolage Grotesque (condensed widths) for display and prices, Figtree for text. Real product photos float slowly in the hero as ambient material.

STORY: The visitor sees how many products are in stock today, searches or browses categories that actually have products, watches how an order moves (cart, payment, preparation, shipment with guía, delivered), and adds to the cart.

FIRST VIEWPORT: White header (mark, MercadoExpress, cart count) with the awning hem; hero on canvas stripes with floating product photos: "11 productos en bodega hoy" pill, display title "Lo que ves aquí, está en bodega.", one line on payment and tracking, the search "¿Qué necesitas hoy?"; the floating "Así va un pedido" card (labelled Ejemplo) with a five-segment progress track cycling the real states. Below: "Por categoría" sections (only categories with products, most products first) with square product cards.

FORM: assigned direction of the third roll, position 6 (egg tray), reshaped by the user's steer into its approved prototype. seed:3f6765b768a17fde. Signature move: the example order card that cycles the five real states with a progress track; secondary: floating real product photos over the canvas stripes.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
