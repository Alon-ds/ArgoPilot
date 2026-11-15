"""Farm lifecycle endpoints."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import Connection, select

from database import connect_database
from schemas import Farm, FarmCreate, FarmPatch
from tables import farms, plots


router = APIRouter(prefix="/v1/farms", tags=["farms"])


def find_farm(connection: Connection, farm_id: str, *, lock: bool = False) -> dict:
    query = select(farms).where(farms.c.id == farm_id)
    if lock:
        query = query.with_for_update()
    row = connection.execute(query).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found.")
    return dict(row)


@router.post("", response_model=Farm, status_code=201)
def create_farm(body: FarmCreate):
    farm = {"id": str(uuid4()), "name": body.name}
    with connect_database(write=True) as connection:
        connection.execute(farms.insert().values(farm))
    return farm


@router.get("", response_model=list[Farm])
def list_farms():
    with connect_database() as connection:
        return [dict(row) for row in connection.execute(select(farms).order_by(farms.c.id)).mappings()]


@router.get("/{farm_id}", response_model=Farm)
def get_farm(farm_id: UUID):
    with connect_database() as connection:
        return find_farm(connection, str(farm_id))


@router.patch("/{farm_id}", response_model=Farm)
def update_farm(farm_id: UUID, body: FarmPatch):
    with connect_database(write=True) as connection:
        farm = find_farm(connection, str(farm_id), lock=True)
        if "name" in body.model_fields_set:
            connection.execute(
                farms.update().where(farms.c.id == str(farm_id)).values(name=body.name)
            )
            farm["name"] = body.name
    return farm


@router.delete("/{farm_id}", status_code=204)
def delete_farm(farm_id: UUID) -> Response:
    with connect_database(write=True) as connection:
        find_farm(connection, str(farm_id), lock=True)
        dependent = select(plots.c.id).where(plots.c.farm_id == str(farm_id)).limit(1)
        if connection.execute(dependent).first() is not None:
            raise HTTPException(status_code=409, detail="Cannot delete a farm with plots.")
        connection.execute(farms.delete().where(farms.c.id == str(farm_id)))
    return Response(status_code=204)
