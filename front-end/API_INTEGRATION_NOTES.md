# Notas de integración con el backend (FastAPI)

Estado al 2026-09-08: backend-api terminó su Fase 1-6 y publicó el contrato
completo en [`../API_CONTRACT.md`](../API_CONTRACT.md). Ese documento es la
fuente de verdad; este archivo solo registra huecos puntuales y decisiones
tomadas del lado del frontend.

`services/*.py` implementa el contrato real:

| Módulo | Endpoints |
|---|---|
| `services/auth.py` | `/auth/register`, `/auth/login` (form-encoded), `/auth/refresh`, `/auth/me` |
| `services/customers.py` | `/customers/me` (GET/PATCH), `/customers/me/addresses` (CRUD), `/customers` (staff, `search=`), `/customers/{id}` |
| `services/products.py` | `/categories`, `/products` (+ `/{id}` de cada uno, `search=`, `include_inactive=` solo staff) |
| `services/inventory.py` | `/inventory` (staff, `low_stock=`, `include_inactive=`, `search=`, `product_id=` repetible), `/inventory/{product_id}` (+ `adjust`, PUT, `history`) |
| `services/orders.py` | `/orders` (POST/GET, `status=`, `search=`, `created_from=`, `created_to=`), `/orders/checkout` (POST), `/orders/{id}`, `/orders/{id}/cancel`, `/orders/{id}/status`, `/orders/{id}/history` |
| `services/payments.py` | `/payments` (POST), `/payments/order/{id}` |
| `services/shipments.py` | `/shipments/order/{id}` (GET/POST), `/shipments/{id}` (PATCH), `/shipments/{id}/ship`, `/shipments/{id}/deliver` |
| `services/reports.py` | `/reports/summary` (staff) + `/inventory?low_stock=true` + `/orders?status=` por etapa para el resumen del panel |

`services/mock_data.py` sigue existiendo solo para que la suite de pruebas de
este proyecto corra sin un backend real levantado (`conftest.py` fuerza
`API_USE_MOCKS=True` en todos los tests). En desarrollo/staging/producción
`API_USE_MOCKS=False` y `MERCADOEXPRESS_API_BASE_URL` deben apuntar al
backend real.

## Cambios 2026-10-23: el panel a escala real y su rediseño

Rama `feat/panel-navigation-scale`, sobre los filtros que backend-api
publicó en el PR #11 (`API_CONTRACT.md`). Medido con la base de desarrollo
(98.483 pedidos, 96.104 clientes, 32.962 productos):

- `/panel/inventario/` pasó de unos 6,5 s a unos 140 ms. Antes recorría las
  ~330 páginas de `GET /inventory` para encontrar los 50 productos en
  pantalla; ahora pide solo esos con `product_id` repetido (máx. 100).
- `services/api_client.py` usa un `httpx.Client` por proceso: las varias
  llamadas de una página reutilizan la conexión (keep-alive).
- Paginación numerada con campo "Ir a la página" en todas las listas
  (`{% pagination page pages %}`), que conserva los filtros de la URL.
- Búsquedas en el servidor: pedidos (`search` por número, correo o nombre del
  cliente; `created_from`/`created_to`, días UTC, así que un pedido hecho de
  noche en Bogotá cuenta para el día siguiente), clientes (`search`),
  productos e inventario (`search`, `category_id`, "solo publicados"),
  inventario "solo stock bajo" (`GET /inventory?low_stock=true` con los
  nombres que trae cada fila; ese endpoint no filtra por categoría).
- `/panel/buscar/?q=` (buscador de la barra superior, atajo `/`) muestra
  pedidos, clientes y productos a la vez, con enlace a cada lista filtrada.
- `/catalogo/admin/` pagina de 50 en 50 (antes mostraba solo los primeros
  100) y las categorías se leen completas página a página (antes se cortaban
  en 100).
- El detalle del pedido y el stock bajo del resumen usan `product_name` /
  `product_sku` de la respuesta; solo si faltan vuelven a `GET /products/{id}`.
- El resumen muestra los pedidos por atender agrupados por etapa (pagados,
  en preparación, enviados) con `GET /orders?status=<etapa>&page_size=5`.
- El riel del panel muestra los totales de pedidos, clientes y productos de
  `GET /reports/summary` (caché de 10 s en el backend); si la llamada falla,
  simplemente no aparecen.

Rediseño del panel ("Boletín de precios", elegido por el usuario): riel verde
bosque, hojas blancas regladas, bandas de grupo, columna de variación,
tipografía Archivo y una escala de 11 verdes (`--g0`..`--g10`). Los estilos
quedaron divididos en `static/css/` (`tokens.css`, `base.css`,
`components/`, `storefront/`, `panel/`) y el JS en módulos ES
(`static/js/app.js` + `static/js/modules/`, más `static/js/panel.js`). La
tienda no cambió de aspecto: se comparó píxel a píxel antes y después.

## Cambios 2026-10-22: checkout en una sola transacción

Rama `feat/momento2-backend`. backend-api agregó `POST /orders/checkout`:
mismo body que `POST /orders` más `method` (pago), y crea pedido, detalle,
reserva de stock, pago y venta en una sola transacción (todo o nada).
`OrderOut` ahora trae `payments: [PaymentOut]`.

- `apps/orders/views.py::checkout` llama a `services/orders.py::checkout`
  (una sola petición) en vez de `POST /orders` + `POST /payments`. Ya no
  existe el caso "pedido creado pero pago sin confirmar": si algo falla no
  se crea nada (409 = stock insuficiente).
- El detalle del pedido en el panel (`/panel/pedidos/<id>/`) muestra
  `order.payments` (método, estado, valor). El detalle del cliente sigue
  leyendo `GET /payments/order/{id}`.
- Ninguna vista llama ya a `POST /payments`. `services/payments.py::create_payment`
  queda solo para el modo mock del checkout y los tests.
- Pendiente: verificar contra el backend real y que la forma quede en
  `API_CONTRACT.md` (lo actualiza backend-api).

## Cambios 2026-10-07: filtros del panel e historial de cambios

Rama `feat/panel-filters-audit`. Formas acordadas con backend-api (ver
`API_CONTRACT.md`):

- **Filtro por estado en `/panel/pedidos/` del lado del servidor.** Antes se
  filtraba solo la página actual en Django; ahora `services/orders.py::list_orders`
  manda `GET /orders?status=<estado>`, así que `total`/`pages` cuentan solo
  los pedidos de ese estado y la paginación conserva el filtro. Un estado
  desconocido en la querystring se ignora (el backend respondería 422). El
  backend acepta `status` repetido; el panel usa uno a la vez.
- **Productos inactivos en `/panel/inventario/` y `/catalogo/admin/`.**
  `GET /products?include_inactive=true` es solo para staff (401 sin token,
  403 para un cliente), así que `list_products(include_inactive=True,
  token=...)` solo se llama desde vistas staff. El inventario los marca con
  "Inactivo". El listado de `/catalogo/admin/` también los pide: antes un
  producto oculto desaparecía de ahí y no había forma de volver a
  publicarlo desde la UI. `GET /inventory` (staff) ahora devuelve por
  defecto solo filas de productos activos (la alerta de stock bajo del
  resumen ya no cuenta descontinuados); el inventario pide
  `include_inactive=true` para cruzar todas las filas.
- **Historial de estados del pedido** (`GET /orders/{id}/history`, staff,
  arreglo sin paginar, del más antiguo al más nuevo): se muestra al final
  de `/panel/pedidos/<id>/` con fecha (hora de Bogotá, filtro
  `api_datetime`), cambio (`from_status` → `to_status` con las etiquetas de
  estado), origen (`ORDER_STATUS_SOURCE_LABELS`) y quién (`actor`, `null` =
  usuario eliminado). Los pedidos anteriores al despliegue no tienen
  entradas (sin backfill): se muestra un mensaje. Si la llamada falla, la
  página carga igual y avisa que no se pudo cargar el historial.
- **Historial de inventario** (`GET /inventory/{product_id}/history`, staff,
  paginado, del más nuevo al más antiguo): nueva página
  `/panel/inventario/<id>/historial/` (enlace "Historial" en cada fila) con
  tipo (`adjust`/`set_levels`), en bodega antes → después (delta), nivel de
  reorden, motivo y quién. Solo registra cambios manuales del staff; las
  reservas/despachos de pedidos se ven en el historial del pedido.
- **El motivo del ajuste ahora sí se envía.** `InventoryAdjustForm` ya
  tenía `reason` y la vista lo pasaba a `POST /inventory/{id}/adjust`, pero
  la plantilla del inventario no mostraba el campo, así que siempre llegaba
  vacío. Ahora hay un input "Motivo (opcional)" junto a la cantidad.
  `set_levels` también acepta `reason` (`PUT /inventory/{id}`), y un `409`
  (en bodega por debajo de lo reservado) muestra un mensaje en español.

## Cambios 2026-10-06: ingresos netos y flujo de envío

Rama `feat/net-revenue-shipping-flow`. Formas acordadas con backend-api
(ver `API_CONTRACT.md`):

- **Resumen del panel (`/panel/`) ahora sale del backend.**
  `services/reports.py` ya no pagina `GET /orders` (5 x 100) ni llama a
  `GET /inventory/{id}` por producto. Usa `GET /reports/summary` (ingresos,
  pedidos por estado, más vendidos, conteo de clientes/productos),
  `GET /inventory?low_stock=true&page_size=100` (se muestran los 10 con menos
  disponible, con el nombre resuelto vía `GET /products/{id}` porque
  `InventoryOut` no trae nombre) y `GET /orders?page=1&page_size=8` para los
  pedidos recientes. Desapareció el aviso de "cifras aproximadas".
- **Ingresos netos.** Un pedido pagado que luego se cancela o reembolsa
  genera un asiento de reversa negativo en el ledger de `Sale`. El resumen
  expone `net_revenue` (lo que muestra la tarjeta principal),
  `gross_revenue`, `refunded_amount` (positivo; `net = gross - refunded`),
  `sale_count` (solo ventas) y `reversal_count`. `total_revenue` ya no
  existe. `top_products` excluye pedidos revertidos.
- **Guía de envío desde "En preparación".** Antes el envío solo se podía
  crear con el pedido en `paid`; si el staff pasaba el pedido a mano a
  `preparing`, nunca podía registrar la guía. Ahora
  `POST /shipments/order/{id}` acepta `paid` o `preparing` (409 en otro
  estado o si ya hay envío) con `{address_id, carrier, tracking_number}`, y
  `PATCH /shipments/{id}` `{carrier, tracking_number}` corrige ambos hasta
  el despacho (409 después). Vacío = `null`; si la guía sigue en `null` al
  despachar, el backend genera `MANUAL-xxxxxxxxxx`. `/ship` exige pedido en
  `preparing`.
- **`ORDER_TRANSITIONS` sin `preparing -> shipped` ni `shipped -> delivered`.**
  Esos pasos solo ocurren con despachar/entregar del envío (que además
  descuentan el stock). Un pedido `shipped` no ofrece cambio manual; la
  tarjeta lo explica. Cancelar/reembolsar a mano libera el stock reservado,
  escribe la reversa si estaba pagado y pasa un envío no despachado a
  `cancelled` (nuevo valor de `ShipmentStatus`, etiqueta "Cancelado"; la
  página del cliente muestra "El envío se canceló junto con el pedido").
- **Inventario del panel (`/panel/inventario/`) sin una llamada por
  producto.** Antes hacía `GET /inventory/{id}` por cada producto y solo
  miraba los primeros 100 productos. Ahora pagina la pantalla (50 productos
  por página vía `GET /products`, orden por nombre) y cruza esa página con
  `GET /inventory` (staff) usando
  `services/inventory.py::availability_by_product`, que lee de a 100 (el
  máximo del backend) y para en cuanto encontró todos los productos de la
  página. Un producto sin fila de inventario sigue apareciendo ("Sin
  registro de inventario"). Ajustar stock y nivel de reorden vuelven a la
  misma página (campo oculto `page`). Ojo: `GET /products` solo lista
  productos activos, así que un producto inactivo no aparece en esta
  pantalla (igual que antes).

## Correcciones 2026-09-12 (estado de pedidos)

- **`OrderOut` ahora incluye `shipping_address`** (objeto `AddressOut`
  resuelto, `null` si el pedido no tiene `shipping_address_id`) además del
  `shipping_address_id` crudo -- ver `API_CONTRACT.md#apiv1orders`. Se usa en
  `templates/orders/detail.html` y `templates/adminpanel/order_detail.html`
  para mostrar la dirección de envío (antes no se mostraba en ninguna
  parte, ni para el cliente ni para administración).
- **El selector de "cambiar estado manualmente" del panel de admin
  (`apps/adminpanel`) ahora solo ofrece los estados a los que el pedido
  puede pasar de verdad** (`services/orders.py::next_statuses`, espejo de
  `_ALLOWED_TRANSITIONS` en `backend-api/app/services/order_service.py`).
  Antes listaba los 8 estados sin importar el estado actual del pedido, así
  que casi cualquier selección que no fuera el único paso válido siguiente
  el backend la rechazaba con `409` ("Transición de estado no válida") --
  esto es lo que hacía parecer que "no se puede cambiar el estado del
  pedido": la mayoría de los intentos fallaban en silencio y por lo tanto el
  cliente tampoco veía ningún cambio reflejado. Un pedido en estado final
  (`delivered`/`cancelled`/`refunded`) ahora muestra un mensaje en vez de un
  selector sin opciones válidas.
- **Todos los estados (pedido/pago/envío) se traducen al español para
  mostrarse** vía `apps/core/templatetags/status_labels.py`
  (`ORDER_STATUS_LABELS`/`PAYMENT_STATUS_LABELS`/`SHIPMENT_STATUS_LABELS` en
  sus respectivos `services/*.py`). Los valores en inglés (`pending`,
  `paid`, etc.) se siguen usando tal cual en querystrings, clases CSS
  (`status--pending`) y el cuerpo del `PATCH`/`POST` -- solo el texto
  visible cambia.
- La insignia de estado de pago en `orders/detail.html` usaba por error la
  clase CSS del *pedido* (`status--{{ order.status }}`) en vez de la del
  pago; corregido a `status--{{ payment.status }}`.

## Corrección 2026-09-12: se eliminó `awaiting_payment`

A pedido explícito, `OrderStatus` se redujo a 7 valores: `pending`, `paid`,
`preparing`, `shipped`, `delivered`, `cancelled`, `refunded` -- ya no existe
`awaiting_payment` (ni en backend-api ni en el frontend). Es un cambio de
esquema real en `backend-api` (migración Alembic
`6bf0432e1cd9_remove_awaiting_payment_from_order_.py`: recrea el tipo nativo
de Postgres `order_status` sin ese valor y traslada las filas existentes en
`awaiting_payment` a `pending`). Un pago fallado deja el pedido en `pending`
en vez de moverlo a `awaiting_payment` -- ya era reintentable desde ahí, así
que el comportamiento no cambia, solo desaparece el estado intermedio.
`services/orders.py::ORDER_STATUSES`/`ORDER_STATUS_LABELS`/
`ORDER_TRANSITIONS` y `apps/orders/views.py::_build_tracker`/`cancellable`
ya no lo referencian.

## Verificado de extremo a extremo contra el backend real

2026-09-08: backend-api añadió un script de seed
(`app/scripts/seed_admin.py`, corre solo en Docker Compose) que provisiona
una cuenta `admin`. Con eso fue posible crear categorías/productos reales
(antes bloqueado -- crear catálogo es `staff`-only y no había forma
self-service de conseguir ese rol) y probar el flujo completo real, no solo
contra datos mock:

- Registro, login (JWT access+refresh), perfil, libreta de direcciones.
- Catálogo real (categorías/productos creados vía API como admin), listado,
  detalle, disponibilidad de inventario.
- Checkout completo: sin direcciones -> redirige a añadir una -> selección
  de dirección -> `POST /orders` -> `POST /payments` automático (gateway
  manual) -> pedido en estado `paid`.
- Ciclo de vida completo del pedido probado avanzando el envío como admin
  (`POST /shipments/order/{id}` -> `.../ship` -> `.../deliver`): el tracker
  visual (`templates/orders/detail.html`) avanzó correctamente por los 5
  pasos (Pedido creado -> Pago confirmado -> Preparando -> Enviado ->
  Entregado) reflejando el estado real del pedido en cada paso.
- Todo esto corriendo Django + FastAPI + PostgreSQL como contenedores
  Docker separados (`docker compose -f ../backend-api/docker-compose.yml -f
  docker-compose.override.yml up`), no solo `runserver` contra un backend
  local.

**Bug real encontrado y corregido durante esta prueba:** el shape de un
line item de pedido (`API_CONTRACT.md`: `{id, product_id, quantity,
unit_price, line_total}`) NO incluye el nombre del producto -- confirmado
contra la respuesta real, no solo la doc (mi mock data sí lo incluía, lo
cual ocultó el problema hasta probar contra el backend real). La página de
detalle de pedido mostraba la columna "Producto" vacía. Corregido en
`apps/orders/views.py::_enrich_items_with_product_names`, que resuelve cada
`product_id` contra `services/products.get_product` (con cache por request)
antes de renderizar.

**Shape real de `GET /shipments/order/{id}` confirmado** (no estaba en
`API_CONTRACT.md`, solo el POST):
```json
{
  "id": "...", "order_id": "...", "address_id": "...",
  "carrier": null, "tracking_number": "MANUAL-XXXXXXXXXX",
  "status": "preparing | in_transit | delivered",
  "shipped_at": null, "delivered_at": null,
  "created_at": "...", "updated_at": "..."
}
```
Coincide con lo que `services/shipments.py` ya asumía (salvo `address_id`/
`created_at`, que el frontend no necesita mostrar). Nota: el `status` del
envío usa su propio vocabulario (`pending`/`preparing`/`in_transit`/
`delivered`/`failed`/`returned`), distinto al `status` del pedido
(`pending`/`paid`/`preparing`/`shipped`/`delivered`/`cancelled`/
`refunded`). Decisión actualizada: la vista de cliente
(`templates/orders/detail.html`) sigue sin mostrar `shipment.status` (solo
transportadora y guía, para no confundir con el estado del pedido), pero el
panel de administración (`templates/adminpanel/order_detail.html`) sí lo
muestra -- staff necesita ver en qué paso de envío está algo antes de decidir
si despachar/entregar, y ambos vocabularios se etiquetan en español por
separado (`SHIPMENT_STATUS_LABELS` vs. `ORDER_STATUS_LABELS`, ver
`apps/core/templatetags/status_labels.py`) para que no se mezclen.

## Huecos pendientes

**RESUELTO:** `GET /api/v1/products?search=<q>` está implementado,
lo usa `services/products.list_products` y ya está documentado en la
sección `/api/v1/products` de `API_CONTRACT.md`.

---

**Nota, no bloqueante:** no hay flujo automático de refresh conectado a las
vistas todavía (los tokens simplemente expiran y el usuario vuelve a hacer
login); se puede añadir un middleware que llame a `/auth/refresh` cuando
`/auth/me` devuelva 401, si se prioriza esa mejora.

---

**CORREGIDO 2026-10-06:** `DELETE /api/v1/categories/{id}` de una categoría
con productos respondía 500: el ORM intentaba poner `products.category_id`
(NOT NULL) a `null` y Postgres lo rechazaba. Ahora `CategoryService.delete`
cuenta los productos antes de borrar y devuelve 409. El frontend ya lo
maneja en `adminpanel.views.category_delete` ("la categoría tiene productos
asociados"). Las subcategorías no bloquean el borrado: quedan con
`parent_id = null`.

## Verificado con `docker compose up` de los tres servicios (integración anterior)

`db` + `api` de `backend-api/docker-compose.yml` + `frontend` de este
`docker-compose.override.yml`: sesión de Django sobreviviendo un restart del
contenedor. Esto encontró y corrigió tres bugs reales de infraestructura, no
de contrato:
- El contexto de build en `docker-compose.override.yml` resolvía al
  directorio equivocado (Compose con `-f` múltiples resuelve rutas relativas
  contra el directorio del *primer* archivo).
- `DJANGO_ENV=production` fuerza redirección HTTPS y cookies `Secure`
  (`config/settings/production.py`); sin proxy TLS delante, un navegador real
  descartaría la cookie de sesión en silencio. El override ahora usa
  `DJANGO_ENV=development` con `DEBUG=False`.
- El `Dockerfile` nunca corría `manage.py migrate`, así que la sqlite de
  sesiones/admin del contenedor no tenía tablas. Se movió `migrate` de build
  time a la orden de arranque (igual que `alembic upgrade head` en
  backend-api), y se le añadió un volumen (`frontend_state`) para que las
  sesiones no se pierdan en cada recreate del contenedor.

## Nota operativa: base de datos de desarrollo compartida

El volumen Docker `backend-api_db_data` es compartido por nombre en este
Docker Desktop -- si el Claude de backend-api también corre
`docker compose up` desde `backend-api/` (con o sin este
`docker-compose.override.yml`), ambos apuntan a la MISMA PostgreSQL de
desarrollo. Se observaron categorías (`Books`, `Electronics`, `Home &
Kitchen`) que este Claude no creó, probablemente de pruebas manuales del
lado de backend. No es un problema -- es solo un aviso: evitar
`docker compose down -v` en este volumen sin coordinar, para no borrar datos
de desarrollo del otro lado.

## Decisiones del frontend (no requieren nada del backend)

- Las URLs de catálogo usan el `id` (UUID) del producto/categoría, no un
  slug -- el contrato no expone slugs.
- El checkout no muestra un formulario de pago: como el backend no tiene
  pasarela real (el gateway manual completa el pago de inmediato), el
  frontend envía el método implícito ("card") en `POST /orders/checkout`,
  que crea el pedido y el pago en una sola transacción.
- Favoritos ("wishlist") es estado de sesión en Django (como el carrito),
  no un endpoint del backend -- no hay recurso "wishlist" en el contrato.
- Las vistas nunca muestran el `detail` de un error del backend (`exc.detail`)
  al usuario. Ese texto está en inglés, es para desarrolladores y a veces
  lleva UUIDs (p. ej. el 409 de stock insuficiente en `POST /orders`). Cada
  `except` muestra un texto fijo en español según el código: 409 = conflicto
  (stock, transición de estado, correo/SKU/categoría duplicados), 422 =
  validación. Ojo: cancelar un pedido que ya no está `pending` devuelve 422
  (`ValidationAppError`), no 409.
