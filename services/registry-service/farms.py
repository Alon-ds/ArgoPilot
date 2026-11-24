"""Farm lifecycle endpoints."""

import sqlite3
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response

from database import connect_database
from schemas import Farm, FarmCreate, FarmPatch


router = APIRouter(prefix="/v1/farms", tags=["farms"])


def find_farm(connection: sqlite3.Connection, farm_id: str) -> dict:
    row = connection.execute("SELECT id, name FROM farms WHERE id = ?", (farm_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found.")
    return dict(row)


@router.post("", response_model=Farm, status_code=201)
def create_farm(body: FarmCreate):
    farm = {"id": str(uuid4()), "name": body.name}
    with connect_database() as connection:
        connection.execute(
            "INSERT INTO farms (id, name) VALUES (?, ?)", (farm["id"], farm["name"])
        )
    return farm


@router.get("", response_model=list[Farm])
def list_farms():
    with connect_database() as connection:
        return [dict(row) for row in connection.execute("SELECT id, name FROM farms ORDER BY id")]


@router.get("/{farm_id}", response_model=Farm)
def get_farm(farm_id: UUID):
    with connect_database() as connection:
        return find_farm(connection, str(farm_id))


@router.get("/{farm_id}/summary")
def get_farm_summary(farm_id: UUID):
    with connect_database() as connection:
        find_farm(connection, str(farm_id))
        row = connection.execute(
            "SELECT COUNT(*) AS plot_count, COALESCE(SUM(area_m2), 0) AS total_area_m2"
            " FROM plots WHERE farm_id = ?",
            (str(farm_id),),
        ).fetchone()
    return {"plot_count": row[0], "total_area_m2": row[1]}


@router.patch("/{farm_id}", response_model=Farm)
def update_farm(farm_id: UUID, body: FarmPatch):
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        farm = find_farm(connection, str(farm_id))
        if "name" in body.model_fields_set:
            connection.execute(
                "UPDATE farms SET name = ? WHERE id = ?", (body.name, str(farm_id))
            )
            farm["name"] = body.name
    return farm


@router.delete("/{farm_id}", status_code=204)
def delete_farm(farm_id: UUID) -> Response:
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        find_farm(connection, str(farm_id))
        if connection.execute(
            "SELECT 1 FROM plots WHERE farm_id = ? LIMIT 1", (str(farm_id),)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Cannot delete a farm with plots.")
        connection.execute("DELETE FROM farms WHERE id = ?", (str(farm_id),))
    return Response(status_code=204)
