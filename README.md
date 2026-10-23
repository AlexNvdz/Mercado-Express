# MercadoExpress

Plataforma de comercio digital del curso Optativa II (Universidad Cooperativa de Colombia, grupo 7792). El repositorio tiene dos proyectos independientes:

- `backend-api/`: API REST con FastAPI, SQLAlchemy y PostgreSQL 16. Es la dueña de todos los datos del negocio (clientes, productos, inventario, pedidos, pagos, envíos y ventas).
- `front-end/`: tienda web y panel administrativo con Django. Consulta la API por HTTP y nunca se conecta directo a la base.

El contrato HTTP entre los dos está en [`API_CONTRACT.md`](API_CONTRACT.md).

## Requisitos

- Docker Desktop.
- [uv](https://docs.astral.sh/uv/) (Python 3.12) para correr los scripts y las pruebas fuera de Docker.

## Cómo ejecutarlo

```bash
cp backend-api/.env.example backend-api/.env   # credenciales por variables de entorno, no en el código
cp front-end/.env.example front-end/.env

docker compose -f backend-api/docker-compose.yml -f front-end/docker-compose.override.yml up --build
```

- Tienda: http://127.0.0.1:8080/
- API y documentación Swagger: http://127.0.0.1:8000/docs
- Panel administrativo: http://127.0.0.1:8080/panel/ (requiere una cuenta `admin`; se crea al arrancar si `FIRST_ADMIN_EMAIL` y `FIRST_ADMIN_PASSWORD` están definidos en `backend-api/.env`)

En Windows usa `127.0.0.1` y no `localhost`. PostgreSQL queda publicado en el puerto `5433` del equipo.

## Cargar el dataset Olist

El script lleva los CSV de Olist (Kaggle, `olistbr/brazilian-ecommerce`) a las tablas de la app: limpia, valida, guarda y reporta cuántas filas entran, se aceptan y se rechazan, con la causa de cada rechazo. Correrlo dos veces no duplica nada.

```bash
cd backend-api
uv sync
uv run python -m app.scripts.load_olist <carpeta_con_los_csv>
```

## Las cuatro operaciones del Momento evaluativo 2

| Operación | Cómo se ejecuta |
|---|---|
| Registrar un pedido con su detalle y su pago en una sola transacción | `POST /api/v1/orders/checkout`, o confirmar una compra en la tienda |
| Consultar un pedido por id con su detalle y sus pagos | `GET /api/v1/orders/{id}` |
| Actualizar el estado de un pedido | `PATCH /api/v1/orders/{id}/status`, o el panel en `/panel/pedidos/` |
| Rechazo: guardar un detalle con un producto que no existe | `uv run python -m app.scripts.demo_rechazo` (desde `backend-api/`) |

Para medir los tiempos de respuesta en milisegundos y los planes de ejecución con y sin índice (con la API encendida y la cuenta admin de `backend-api/.env`):

```bash
uv run python -m app.scripts.benchmark
```

## Pruebas

```bash
cd backend-api && uv run pytest   # usa la base mercadoexpress_test (ver backend-api/README.md)
cd front-end && uv run pytest     # no necesita el backend encendido
```

Los detalles de cada proyecto están en [`backend-api/README.md`](backend-api/README.md) y [`front-end/README.md`](front-end/README.md).
