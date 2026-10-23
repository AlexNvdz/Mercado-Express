# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Staff (`employee` / `admin`)** run the store from the panel at `/panel/` and `/catalogo/admin/`: they move orders through payment, preparation, shipment and delivery, correct statuses, keep stock right, and maintain products, categories and images. They work on desktop and on phones (the user has asked twice for phone layouts that do not clip or wrap badly).
- **Customers** browse the catalog, keep a session cart and wishlist, check out to a saved address, and follow their orders.
- The project is also a university deliverable: the team demos it to a professor, so the panel has to hold up under real data, not only demo rows.

## Product Purpose

MercadoExpress is an online grocery market. A Django frontend talks only over HTTP to a FastAPI backend that owns every business record (customers, products, inventory, orders, payments, shipments, the sales ledger). Success: staff find any order, customer or product in seconds at full data volume, and customers buy without friction.

## Positioning

An honest, end-to-end store whose numbers come from an append-only sales ledger and an audited order and stock history, not from editable totals. The panel shows what really happened (who changed what, when, from which status) instead of a decorative dashboard.

## Operating Context

- Data volume in the dev database (2026-10-22, after loading the Olist dataset): 98,483 orders, 96,105 users, 32,962 products (11 active, 32,951 inactive Olist products), 74 categories, 102,210 order lines. Every list must page and search server-side.
- Order flow: `pending -> paid -> preparing -> shipped -> delivered`, with `cancelled` / `refunded` branches. Payments and shipments drive the normal flow; the manual status override is for corrections only.
- Money is Colombian pesos shown as `$6.500`; dates render in `America/Bogota`.
- Staff accounts are provisioned in the database (no self sign-up).

## Capabilities and Constraints

- Server-rendered Django templates, vanilla JavaScript, no build step. Static files are served by whitenoise.
- Views never call the backend directly; everything goes through `services/*.py`. `API_CONTRACT.md` (repo root) is the source of truth for the HTTP contract.
- Search exists today for products (name or SKU, plus category). Order search (number, customer, dates), customer search and an inventory product filter are requested from backend-api and not shipped yet.
- No real payment gateway or carrier: checkout pays immediately through a manual gateway (`POST /orders/checkout`), and shipments carry a manual carrier and tracking number.
- Status values stay in English on the wire, in querystrings and CSS classes; the UI shows Spanish labels only.
- Confirmations use the styled shared `<dialog>` (`data-confirm`), never the browser's native `confirm()`.
- Today all styling is one `static/css/base.css` (about 1,350 lines) and all behavior is one `static/js/app.js`. The user asked to split both into organized files.

## Brand Commitments

- Name: MercadoExpress. UI copy in Spanish.
- Color identity is pinned by the user (2026-10-22): forest green text (`--ink` #17382a), action green (`--volt` #2e7d50), lime highlight (`--signal` #c8e46e), pale-mint canvas (#f3f8f2) and white surfaces. New tones and shades may be added when needed; the identity stays.
- Everything else (type, layout, components, navigation) is open to a full renewal, which must avoid generic AI-looking design.
- Rejected on 2026-10-22: the "mercado campesino" storefront trial (slate/pizarra green, kraft-paper tags, scalable section index, animated hero). Do not reuse it.

## Evidence on Hand

- Real seed catalog (`backend-api/app/scripts/seed_demo_data.py`) with product photos uploaded through the panel; the Olist order history (2016-2018) and its customers.
- No testimonials, reviews, press, partners or delivery-time promises exist. Do not invent them.

## Product Principles

1. Find before browse: any record is one search away at full volume.
2. Show the record's truth: ledger figures, audited history and real stock, never decorative numbers.
3. Same task, any screen: every staff action works on a phone without horizontal scrolling of the page.
4. Spanish and plain: labels say what happens, in the customer's and the employee's words.

## Accessibility & Inclusion

Assumed (not yet confirmed by the user): WCAG 2.1 AA contrast, full keyboard use of the panel, visible focus, and touch targets of at least 44px on phones.
