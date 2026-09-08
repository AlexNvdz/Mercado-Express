# Notas de integración con el backend (FastAPI)

Estado al 2026-09-08: backend-api terminó su Fase 1-6 y publicó el contrato
completo en [`../API_CONTRACT.md`](../API_CONTRACT.md). Ese documento es la
fuente de verdad; este archivo solo registra huecos puntuales y decisiones
tomadas del lado del frontend.

`services/*.py` implementa el contrato real:

| Módulo | Endpoints |
|---|---|
| `services/auth.py` | `/auth/register`, `/auth/login` (form-encoded), `/auth/refresh`, `/auth/me` |
| `services/customers.py` | `/customers/me` (GET/PATCH), `/customers/me/addresses` (CRUD) |
| `services/products.py` | `/categories`, `/products` (+ `/{id}` de cada uno, `search=`) |
| `services/inventory.py` | `/inventory/{product_id}` |
| `services/orders.py` | `/orders` (POST/GET), `/orders/{id}`, `/orders/{id}/cancel` |
| `services/payments.py` | `/payments` (POST), `/payments/order/{id}` |
| `services/shipments.py` | `/shipments/order/{id}` |

`services/mock_data.py` sigue existiendo solo para que la suite de pruebas de
este proyecto corra sin un backend real levantado (`conftest.py` fuerza
`API_USE_MOCKS=True` en todos los tests). En desarrollo/staging/producción
`API_USE_MOCKS=False` y `MERCADOEXPRESS_API_BASE_URL` deben apuntar al
backend real.

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
envío usa su propio vocabulario (`preparing`/`in_transit`/`delivered`),
distinto al `status` del pedido (`preparing`/`shipped`/`delivered`) -- el
frontend no muestra `shipment.status` directamente para evitar esa
confusión, solo transportadora y guía.

## Huecos pendientes

**ENDPOINT SOLICITADO (mejora, no bloqueante):**
METHOD: GET
URL: `/api/v1/products?search=<q>` — ya implementado y confirmado
funcionando (`services/products.list_products` lo usa). Pendiente: no está
documentado todavía en `API_CONTRACT.md` -- pedir al backend que lo agregue
a la sección `/api/v1/products`.

---

**Nota, no bloqueante:** no hay flujo automático de refresh conectado a las
vistas todavía (los tokens simplemente expiran y el usuario vuelve a hacer
login); se puede añadir un middleware que llame a `/auth/refresh` cuando
`/auth/me` devuelva 401, si se prioriza esa mejora.

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
  pasarela real (`POST /payments` completa el pago de inmediato con el
  gateway manual), el frontend solo pide método de pago implícito ("card")
  y llama a `POST /payments` justo después de crear el pedido.
- Favoritos ("wishlist") es estado de sesión en Django (como el carrito),
  no un endpoint del backend -- no hay recurso "wishlist" en el contrato.
