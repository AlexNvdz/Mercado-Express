"""Aggregates every v1 sub-router under a single APIRouter, mounted in
app/main.py at settings.API_V1_PREFIX."""

from fastapi import APIRouter

from app.routers.v1 import (
    auth,
    categories,
    customers,
    inventory,
    orders,
    payments,
    products,
    shipments,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(inventory.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(shipments.router)
