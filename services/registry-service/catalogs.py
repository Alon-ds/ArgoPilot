"""Read-only crop, soil, and emitter catalogs."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from database import connect_database
from schemas import Crop, Emitter, Soil
from tables import metadata


router = APIRouter(prefix="/v1")
Catalog = Literal["crops", "soils", "emitters"]


def list_catalog(table: Catalog) -> list[dict]:
    catalog = metadata.tables[table]
    with connect_database() as connection:
        return [dict(row) for row in connection.execute(select(catalog).order_by(catalog.c.id)).mappings()]


def get_catalog_item(table: Catalog, item_id: str) -> dict:
    catalog = metadata.tables[table]
    with connect_database() as connection:
        row = connection.execute(select(catalog).where(catalog.c.id == item_id)).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Item not found in {table}.")
    return dict(row)


@router.get("/crops", response_model=list[Crop])
def list_crops():
    return list_catalog("crops")


@router.get("/crops/{item_id}", response_model=Crop)
def get_crop(item_id: str):
    return get_catalog_item("crops", item_id)


@router.get("/soils", response_model=list[Soil])
def list_soils():
    return list_catalog("soils")


@router.get("/soils/{item_id}", response_model=Soil)
def get_soil(item_id: str):
    return get_catalog_item("soils", item_id)


@router.get("/emitters", response_model=list[Emitter])
def list_emitters():
    return list_catalog("emitters")


@router.get("/emitters/{item_id}", response_model=Emitter)
def get_emitter(item_id: str):
    return get_catalog_item("emitters", item_id)
