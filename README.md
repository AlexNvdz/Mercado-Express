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

## Envíos con Envia.com y el webhook de rastreo

Con `ENVIA_API_KEY` en `backend-api/.env` (sandbox de Envia), al pagar un pedido el backend compra la guía más barata y el pedido pasa a "En preparación". Si falla (sin teléfono, ciudad sin cobertura), el panel lo muestra en "Pedidos pagados sin guía" con el botón "Reintentar guías". Envia avisa los cambios de la transportadora por un webhook (`POST /api/v1/webhooks/envia?token=...`): recogido pasa el pedido a "Enviado" y entregado a "Entregado", sin que nadie toque el panel.

Envia está en internet y el backend en tu equipo, así que el webhook necesita un túnel público con [ngrok](https://ngrok.com) (una vez: `winget install Ngrok.Ngrok`, `ngrok update` y `ngrok config add-authtoken <tu_token>`). La URL de ngrok cambia en cada arranque; el script `scripts\demo-envia.ps1` abre el túnel y le avisa a Envia la URL nueva:

```powershell
# Con el stack de Docker ya encendido (comando de arriba): solo túnel + webhook
powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1 -ApiPort 8000 -WebPort 8080 -Db mercadoexpress

# Sin Docker para la app: levanta la API en 8001 y Django en 8081 contra la base de prueba migcheck_envia
powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1

# Sin internet o sin ngrok: todo menos el túnel (los botones manuales del panel siguen funcionando)
powershell -ExecutionPolicy Bypass -File scripts\demo-envia.ps1 -NoTunnel
```

Requisitos en `backend-api/.env`: `ENVIA_API_KEY`, `ENVIA_WEBHOOK_TOKEN` (cualquier texto largo y aleatorio) y, para verificar la firma de Envia, `ENVIA_WEBHOOK_SECRET` (lo imprime `uv run python -m app.scripts.envia_webhook <url>`). En el sandbox la guía nunca avanza sola: para la demo se dispara el aviso con el probador de Envia (`POST https://api-test.envia.com/ship/webhooktest/`) o con los botones "Despachar" y "Marcar entregado" del panel. Cierra la ventana de ngrok al terminar: mientras está abierta, la API se puede alcanzar desde internet.

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
