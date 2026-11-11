"""Envia.com client (https://docs.envia.com): shipping labels on the Shipping
API (Bearer ENVIA_API_KEY) and Colombian place lookups on the public, keyless
geocodes host. It knows Envia's wire format and nothing about orders:
ShipmentService decides when to call it.

The Shipping API reports business errors as HTTP 200 with
`{"meta": "error", "error": {"message": ...}}`, so every response is checked
for that, not only for the status code.
"""

import asyncio
import logging
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

# tests/conftest.py swaps in an httpx.MockTransport; None = the real network.
transport: httpx.AsyncBaseTransport | None = None

# shortcut: unbounded, process-local; fine for 33 departments and the cities
# customers type, switch to an LRU if it ever grows.
_geo_cache: dict[str, Any] = {}

# Raised by the parsing below when Envia answers with an unexpected shape.
_PARSE_ERRORS = (KeyError, IndexError, TypeError, ValueError, ArithmeticError)


def enabled() -> bool:
    """Shipping labels are bought only with a key; without one shipments stay manual."""
    return bool(settings.ENVIA_API_KEY)


@dataclass(frozen=True)
class Place:
    state_code: str  # Envia's 2-letter department code, e.g. "AN"
    dane_code: str  # 8-digit DANE municipality code: what Envia wants in `city`
    postal_code: str


@dataclass(frozen=True)
class Rate:
    carrier: str
    service: str
    total_price: Decimal


@dataclass(frozen=True)
class Label:
    carrier: str
    service: str
    tracking_number: str
    tracking_url: str | None
    label_url: str
    total_price: Decimal


def _client(base_url: str, headers: dict[str, str] | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url, headers=headers, timeout=settings.ENVIA_TIMEOUT_SECONDS, transport=transport
    )


def _fold(text: str) -> str:
    """Case- and accent-insensitive form: "Bogotá" and "bogota" match."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold().strip()


# --- Geocodes (public): departments, cities, DANE and postal codes ---


async def _geo(path: str) -> Any:
    if path in _geo_cache:
        return _geo_cache[path]
    try:
        async with _client(settings.ENVIA_GEOCODES_URL) as client:
            response = await client.get(path)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ExternalServiceError(
            f"No se pudo consultar las ciudades de Envia ({type(exc).__name__})."
        ) from exc
    _geo_cache[path] = data
    return data


# Envia uses two code sets for the same departments: its shipping API and
# geocodes' /locate take the first code (Cundinamarca = "CN", Cauca = "CU"),
# geocodes' /list/localities the second (Cundinamarca = "CU"). Each row was
# checked by locating the department's main city with its first code.
# (name, shipping code, localities-list code)
DEPARTMENTS: tuple[tuple[str, str, str], ...] = (
    ("Amazonas", "AM", "AM"),
    ("Antioquia", "AN", "AN"),
    ("Arauca", "AR", "AR"),
    ("Archipiélago de San Andrés", "SA", "SA"),
    ("Atlántico", "AT", "AT"),
    ("Bogotá", "DC", "DC"),
    ("Bolívar", "BL", "BL"),
    ("Boyacá", "BY", "BY"),
    ("Caldas", "CL", "CL"),
    ("Caquetá", "CA", "CQ"),
    ("Casanare", "CS", "CS"),
    ("Cauca", "CU", "CA"),
    ("Cesar", "CE", "CE"),
    ("Chocó", "CH", "CH"),
    ("Córdoba", "CO", "CO"),
    ("Cundinamarca", "CN", "CU"),
    ("Guainía", "GU", "GN"),
    ("Guaviare", "GA", "GV"),
    ("Huila", "HU", "HU"),
    ("La Guajira", "LG", "LG"),
    ("Magdalena", "MA", "MA"),
    ("Meta", "ME", "ME"),
    ("Nariño", "NA", "NA"),
    ("Norte de Santander", "NS", "NS"),
    ("Putumayo", "PU", "PU"),
    ("Quindío", "QU", "QD"),
    ("Risaralda", "RI", "RI"),
    ("Santander", "SN", "ST"),
    ("Sucre", "SU", "SU"),
    ("Tolima", "TO", "TO"),
    ("Valle del Cauca", "VC", "VC"),
    ("Vaupés", "VA", "VP"),
    ("Vichada", "VI", "VD"),
)


def states() -> list[dict[str, str]]:
    """The 33 departments as `{"code", "name"}`; `code` is the shipping one."""
    return [{"code": code, "name": name} for name, code, _ in DEPARTMENTS]


def state_code(state: str) -> str | None:
    """Shipping code for a department given by that code ("AN") or its name."""
    folded = _fold(state)
    for name, code, _ in DEPARTMENTS:
        if folded in (_fold(code), _fold(name)):
            return code
    return None


async def cities(code: str) -> list[str]:
    """Every locality Envia knows in the department (towns and veredas), sorted."""
    list_code = next(lc for _, c, lc in DEPARTMENTS if c == code)
    data = await _geo(f"/list/localities/CO/{list_code}")
    return sorted({loc["name"] for loc in data}, key=_fold)


async def locate(state: str, city: str) -> Place | None:
    """None when the department or the city is unknown to Envia."""
    code = state_code(state)
    if code is None or not city.strip():
        return None
    data = await _geo(f"/locate/CO/{code}/{quote(city.strip(), safe='')}")
    try:
        zip_code = data[0]["zip_codes"][0]
        return Place(
            state_code=code, dane_code=zip_code["info"]["stat_8digit"], postal_code=zip_code["zip_code"]
        )
    except _PARSE_ERRORS:
        return None


# --- Shipping API (Bearer key): rates, labels, tracking, cancellation ---


async def _ship(path: str, body: dict[str, Any]) -> Any:
    headers = {"Authorization": f"Bearer {settings.ENVIA_API_KEY}"}
    try:
        async with _client(settings.ENVIA_BASE_URL, headers) as client:
            response = await client.post(path, json=body)
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Envia no respondió ({type(exc).__name__}).") from exc
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if response.status_code >= 400 or not isinstance(payload, dict) or payload.get("meta") == "error":
        error = payload.get("error") if isinstance(payload, dict) else None
        message = error.get("message") if isinstance(error, dict) else response.text[:200]
        raise ExternalServiceError(f"Envia rechazó la solicitud: {message}")
    return payload.get("data")


def address(
    name: str, phone: str, line1: str, place: Place, email: str | None = None, reference: str | None = None
) -> dict[str, Any]:
    """Envia wants street and house number apart: a Colombian "Calle 10 # 5-20"
    is split at the "#" ("S/N" when there is none)."""
    street, _, number = line1.partition("#")
    body = {
        "name": name,
        "phone": phone,
        "street": street.strip(),
        "number": number.strip() or "S/N",
        "city": place.dane_code,
        "state": place.state_code,
        "country": "CO",
        "postalCode": place.postal_code,
    }
    if email:
        body["email"] = email
    if reference:
        body["reference"] = reference
    return body


def package(declared_value: Decimal) -> dict[str, Any]:
    """One box per order with the configured size (products carry no weight)."""
    return {
        "type": "box",
        "content": "Productos MercadoExpress",
        "amount": 1,
        "declaredValue": float(declared_value),
        "weight": settings.ENVIA_PACKAGE_WEIGHT_KG,
        "weightUnit": "KG",
        "lengthUnit": "CM",
        "dimensions": {
            "length": settings.ENVIA_PACKAGE_LENGTH_CM,
            "width": settings.ENVIA_PACKAGE_WIDTH_CM,
            "height": settings.ENVIA_PACKAGE_HEIGHT_CM,
        },
    }


async def rates(origin: dict[str, Any], destination: dict[str, Any], parcel: dict[str, Any]) -> list[Rate]:
    """Every service of every ENVIA_CARRIERS carrier (Envia quotes one carrier
    per call, so they go in parallel). A carrier that fails or doesn't cover
    the address is skipped; raises only if none quoted."""

    async def one(carrier: str) -> list[Rate]:
        data = await _ship(
            "/ship/rate/",
            {
                "origin": origin,
                "destination": destination,
                "packages": [parcel],
                "shipment": {"type": 1, "carrier": carrier},
                "settings": {"currency": "COP"},
            },
        )
        try:
            return [
                Rate(r["carrier"], r["service"], Decimal(str(r["totalPrice"])))
                for r in data
                # Cash on delivery: the carrier would charge the customer again.
                if not r["service"].endswith("_cod") and r["service"] not in settings.ENVIA_EXCLUDED_SERVICES
            ]
        except _PARSE_ERRORS as exc:
            raise ExternalServiceError(f"Respuesta inesperada de Envia al cotizar con {carrier}.") from exc

    results = await asyncio.gather(*(one(c) for c in settings.ENVIA_CARRIERS), return_exceptions=True)
    found: list[Rate] = []
    errors: list[str] = []
    for carrier, result in zip(settings.ENVIA_CARRIERS, results, strict=True):
        if isinstance(result, BaseException):
            detail = result.detail if isinstance(result, ExternalServiceError) else repr(result)
            logger.warning("Envia rate for %s failed: %s", carrier, detail)
            errors.append(f"{carrier}: {detail}")
        else:
            found.extend(result)
    if not found:
        raise ExternalServiceError("Ninguna transportadora cotizó este envío. " + " | ".join(errors))
    return found


async def generate(
    origin: dict[str, Any], destination: dict[str, Any], parcel: dict[str, Any], rate: Rate
) -> Label:
    """Buys the label (charged to the Envia account balance)."""
    data = await _ship(
        "/ship/generate/",
        {
            "origin": origin,
            "destination": destination,
            "packages": [parcel],
            "shipment": {"type": 1, "carrier": rate.carrier, "service": rate.service},
            "settings": {"currency": "COP", "printFormat": "PDF", "printSize": "STOCK_4X6"},
        },
    )
    try:
        label = data[0]
        return Label(
            carrier=label["carrier"],
            service=label["service"],
            tracking_number=label["trackingNumber"],
            tracking_url=label.get("trackUrl"),
            label_url=label["label"],
            total_price=Decimal(str(label["totalPrice"])),
        )
    except _PARSE_ERRORS as exc:
        raise ExternalServiceError("Respuesta inesperada de Envia al generar la guía.") from exc


async def track(tracking_number: str) -> str:
    """Envia's status name for the label, e.g. "Created", "Picked Up", "Delivered"."""
    data = await _ship("/ship/generaltrack/", {"trackingNumbers": [tracking_number]})
    try:
        return str(data[0]["status"])
    except _PARSE_ERRORS as exc:
        raise ExternalServiceError("Respuesta inesperada de Envia al rastrear la guía.") from exc


async def cancel_quietly(carrier: str, tracking_number: str) -> None:
    """Voids an undispatched label so Envia returns its cost to the balance.
    BackgroundTask after the order's cancellation commits: a failure only
    logs, the order stays cancelled either way."""
    try:
        await _ship("/ship/cancel/", {"carrier": carrier, "trackingNumber": tracking_number})
    except Exception:
        logger.warning("Envia cancel of %s %s failed", carrier, tracking_number, exc_info=True)
