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
| `services/products.py` | `/categories`, `/products` (+ `/{id}` de cada uno) |
| `services/inventory.py` | `/inventory/{product_id}` |
| `services/orders.py` | `/orders` (POST/GET), `/orders/{id}`, `/orders/{id}/cancel` |
| `services/payments.py` | `/payments` (POST), `/payments/order/{id}` |
| `services/shipments.py` | `/shipments/order/{id}` |

`services/mock_data.py` sigue existiendo solo para que la suite de pruebas de
este proyecto corra sin un backend real levantado (`conftest.py` fuerza
`API_USE_MOCKS=True` en todos los tests). En desarrollo/staging/producción
`API_USE_MOCKS=False` y `MERCADOEXPRESS_API_BASE_URL` deben apuntar al
backend real.

## Huecos / cosas a confirmar con backend-api

**ENDPOINT SOLICITADO / ACLARACIÓN:**
METHOD: GET
URL: `/api/v1/shipments/order/{order_id}`
MOTIVO: `API_CONTRACT.md` documenta el body de `POST /shipments/order/{id}`
pero no el shape de la respuesta de este GET. `services/shipments.py` asume
`{id, order_id, carrier, tracking_number, status, shipped_at, delivered_at}`
-- confirmar nombres de campo exactos (o el shape real) para ajustar el
template `templates/orders/detail.html`.

---

**ENDPOINT SOLICITADO (mejora, no bloqueante):**
METHOD: GET
URL: `/api/v1/products?search=<q>` (o `?q=<q>`)
MOTIVO: `GET /products` solo acepta `category_id`, `page`, `page_size` -- no
hay búsqueda de texto server-side. El buscador del navbar (`templates/partials/navbar.html`)
hoy filtra en el frontend sobre la página ya traída (ver comentario en
`services/products.list_products`), lo cual no busca en todo el catálogo si
hay más de una página de productos.

---

**Confirmado contra el backend real** (2026-09-08, `docker compose up` en
`backend-api/` + smoke test manual): `/auth/register`, `/auth/login`
(form-encoded), `/auth/me`, `/auth/refresh` (devuelve
`{"access_token", "token_type"}`, sin rotar el refresh token),
`/customers/me`, `/customers/me/addresses` (GET/POST, respuesta es un array
plano, no paginado), paginación de `/categories`/`/products`/`/orders`, y el
formato de error 404 y 422 (este último es una lista de errores por campo,
no un string -- `services/exceptions.ApiError.detail` ya la concatena).

No hay flujo automático de refresh conectado a las vistas todavía (los
tokens simplemente expiran y el usuario vuelve a hacer login); se puede
añadir un middleware que llame a `/auth/refresh` cuando `/auth/me` devuelva
401, si se prioriza esa mejora.

**No verificado end-to-end** (catálogo/pedidos/pagos/envíos reales): el
backend no trae datos semilla y la creación de categorías/productos es
`staff`-only; no hay forma self-service de obtener un rol `employee` (por
diseño, ver `../backend-api/README.md`). Sin productos reales no se pudo
probar `POST /orders` con éxito ni el flujo completo de pago/envío contra la
base de datos real -- sí se validó que create_order responde `404` cuando el
`shipping_address_id` no es del cliente o el producto no existe, que es el
comportamiento esperado. El shape de `GET /shipments/order/{id}` sigue sin
confirmarse por la misma razón (ver arriba).

**Verificado con `docker compose up` de los tres servicios** (`db` + `api`
de `backend-api/docker-compose.yml` + `frontend` de este
`docker-compose.override.yml`): registro, login, perfil y direcciones
funcionando de extremo a extremo Django -> FastAPI -> PostgreSQL, sesión de
Django sobreviviendo un restart del contenedor. Esto encontró y corrigió tres
bugs reales, no solo de integración con el contrato:
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

## Decisiones del frontend (no requieren nada del backend)

- Las URLs de catálogo usan el `id` (UUID) del producto/categoría, no un
  slug -- el contrato no expone slugs.
- El checkout no muestra un formulario de pago: como el backend no tiene
  pasarela real (`POST /payments` completa el pago de inmediato con el
  gateway manual), el frontend solo pide método de pago implícito ("card")
  y llama a `POST /payments` justo después de crear el pedido.
