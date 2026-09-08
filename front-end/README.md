# MercadoExpress - Frontend (Django)

Frontend web de MercadoExpress. Consume la API REST del backend
(`../backend-api`, Python + FastAPI + PostgreSQL) por HTTP; no implementa
lógica de negocio ni se conecta directamente a PostgreSQL.

```
Django (este proyecto)  ->  HTTP/REST  ->  FastAPI  ->  PostgreSQL
```

El contrato completo vive en [`../API_CONTRACT.md`](../API_CONTRACT.md)
(mantenido por backend-api). [`API_INTEGRATION_NOTES.md`](./API_INTEGRATION_NOTES.md)
registra qué se verificó contra el backend real, qué sigue pendiente de
confirmar, y decisiones tomadas del lado del frontend.

## Estructura

```
config/            settings (base/development/production), urls, wsgi/asgi
apps/
  core/            home
  catalog/         categorías, listado (búsqueda + paginación), detalle,
                    favoritos ("wishlist", estado de sesión)
  cart/            carrito (estado de sesión, no es negocio del backend)
  accounts/        login, registro, logout (contra la API)
  dashboard/       área autenticada del cliente (perfil editable,
                    direcciones con predeterminada)
  orders/          checkout, historial (filtro por estado, repetir pedido),
                    detalle con tracker visual del pedido
services/          única capa que habla HTTP con el backend
  api_client.py    cliente HTTP genérico (httpx), maneja errores/timeouts
  auth.py          registro/login (JWT)/refresh/sesión
  customers.py     perfil y libreta de direcciones
  products.py      catálogo (categorías, productos, búsqueda, paginación)
  inventory.py     disponibilidad de stock
  orders.py        pedidos (crear, listar, detalle, cancelar)
  payments.py      pagos (gateway manual del backend)
  shipments.py     seguimiento de envío
  mock_data.py     datos usados solo por la suite de tests (ver conftest.py)
templates/         plantillas Django (base + partials + una carpeta por app)
static/            CSS/JS propios (whitenoise sirve staticfiles)
tests/             pruebas de la capa services/
apps/*/tests/      pruebas de vistas por app
conftest.py        fuerza API_USE_MOCKS=True para toda la suite de tests
```

Ninguna vista o plantilla hace llamadas HTTP directamente: todas pasan por
`services/`.

## Funciones

Catálogo con búsqueda server-side, filtro por categoría y paginación;
detalle de producto con disponibilidad real y selector de cantidad;
favoritos (heart toggle, estado de sesión); carrito con actualización en
vivo; checkout con selección/alta de dirección de envío y pago automático
(gateway manual del backend); historial de pedidos con pestañas por estado
y "repetir pedido"; detalle de pedido con tracker visual del ciclo de vida,
pago y envío; perfil editable y libreta de direcciones con predeterminada.

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Para probar contra el backend real: Docker (o `backend-api` corriendo con
  `uv run uvicorn` + PostgreSQL local) -- ver `../backend-api/README.md`.

## Desarrollo local

```bash
cp .env.example .env      # ajustar si es necesario
uv sync
uv run manage.py migrate  # tablas internas de Django (sesiones/admin), no negocio
uv run manage.py runserver
```

`.env.example` trae `API_USE_MOCKS=False` por defecto: el frontend llama al
backend real en `MERCADOEXPRESS_API_BASE_URL` (por defecto
`http://localhost:8000`), que debe estar corriendo (ver
`../backend-api/README.md` o la sección Docker abajo). Para trabajar en la
UI sin levantar el backend, pon `API_USE_MOCKS=True` en tu `.env` -- sirve
datos de `services/mock_data.py` (usuario demo:
`cliente.demo@mercadoexpress.test` / `demo1234`).

## Variables de entorno

Ver [`.env.example`](./.env.example). Nunca hardcodear
`MERCADOEXPRESS_API_BASE_URL` ni secretos en el código.

## Tests

```bash
uv run pytest
```

`conftest.py` fuerza `API_USE_MOCKS=True` para toda la suite, así que corre
sin necesidad de un backend real levantado. Cubren: páginas (home, catálogo,
carrito, cuenta, direcciones, pedidos), la capa de servicios
(`services/api_client.py` con HTTP simulado vía `unittest.mock`, y cada
módulo de `services/`), autenticación basada en sesión (par de tokens JWT),
el carrito, checkout (dirección + pago automático) y cancelación de pedidos.

## Docker

### Solo el frontend

```bash
docker build -t mercadoexpress-frontend .
docker run --env-file .env -p 8080:8000 mercadoexpress-frontend
```

### Los tres servicios (db + api + frontend) -- verificado end-to-end

`docker-compose.override.yml` añade el servicio `frontend` al
`docker-compose.yml` de `backend-api` (que trae `db` + `api`; no hay
compose raíz aún -- ver `../backend-api/README.md#docker`). El orden de los
`-f` importa (ver comentario en el archivo):

```bash
docker compose -f ../backend-api/docker-compose.yml -f docker-compose.override.yml up --build
```

Levanta PostgreSQL, FastAPI (`http://localhost:8000`) y Django
(`http://localhost:8080`), con Django llamando a FastAPI por la red interna
de Docker (`http://api:8000`). Registro, login, perfil y direcciones se
probaron de extremo a extremo sobre este stack -- ver
`API_INTEGRATION_NOTES.md` para los bugs de Docker/config que esa prueba
encontró y corrigió (build context, cookies `Secure` sin TLS, migraciones no
aplicadas en el contenedor).

Con la cuenta admin sembrada por `backend-api` (`app/scripts/seed_admin.py`,
`FIRST_ADMIN_EMAIL`/`FIRST_ADMIN_PASSWORD` en su `.env`) se probó también
catálogo real, checkout, pago y el ciclo de vida completo de un pedido
(pendiente -> pagado -> preparando -> enviado -> entregado) contra
PostgreSQL real -- ver `API_INTEGRATION_NOTES.md` para el bug real que esa
prueba encontró (nombre de producto ausente en los items del pedido) y el
shape confirmado de `GET /shipments/order/{id}`.

**Nota:** el volumen de PostgreSQL (`backend-api_db_data`) se comparte por
nombre en Docker Desktop -- si el Claude de backend-api también tiene el
stack levantado, ambos usan la misma base de datos de desarrollo. Ver el
aviso en `API_INTEGRATION_NOTES.md` antes de correr `docker compose down -v`.

## Levantar el stack completo manualmente (sin Docker)

1. PostgreSQL + FastAPI: seguir `../backend-api/README.md` (`docker compose
   up -d db`, `uv run alembic upgrade head`, `uv run uvicorn app.main:app --reload`).
2. Django: `uv run manage.py migrate && uv run manage.py runserver`, con
   `.env` apuntando `MERCADOEXPRESS_API_BASE_URL=http://localhost:8000` y
   `API_USE_MOCKS=False`.
