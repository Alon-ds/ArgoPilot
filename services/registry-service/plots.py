"""Plot lifecycle endpoints and farm filtering."""

import sqlite3
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response

from database import connect_database
from schemas import Plot, PlotCreate, PlotPatch


router = APIRouter(prefix="/v1/plots", tags=["plots"])


def find_plot(connection: sqlite3.Connection, plot_id: str) -> dict:
    row = connection.execute("SELECT * FROM plots WHERE id = ?", (plot_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Plot not found.")
    return dict(row)


def validate_references(connection: sqlite3.Connection, plot: dict) -> None:
    for field, table in (
        ("farm_id", "farms"),
        ("crop_id", "crops"),
        ("soil_id", "soils"),
        ("emitter_id", "emitters"),
    ):
        if connection.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (plot[field],)
        ).fetchone() is None:
            raise HTTPException(status_code=422, detail=f"{field} does not exist.")


def validate_unique_name(connection: sqlite3.Connection, plot: dict) -> None:
    if connection.execute(
        "SELECT 1 FROM plots WHERE farm_id = ? AND name = ? AND id != ?",
        (plot["farm_id"], plot["name"], plot["id"]),
    ).fetchone():
        raise HTTPException(status_code=409, detail="A plot with this name already exists in the farm.")


@router.post("", response_model=Plot, status_code=201)
def create_plot(body: PlotCreate):
    plot = {"id": str(uuid4()), **body.model_dump(mode="json")}
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        validate_references(connection, plot)
        validate_unique_name(connection, plot)
        columns = ", ".join(plot)
        placeholders = ", ".join("?" for _ in plot)
        connection.execute(
            f"INSERT INTO plots ({columns}) VALUES ({placeholders})", tuple(plot.values())
        )
    return plot


@router.get("", response_model=list[Plot])
def list_plots(farm_id: UUID | None = None):
    with connect_database() as connection:
        if farm_id is None:
            rows = connection.execute("SELECT * FROM plots ORDER BY id")
        else:
            rows = connection.execute(
                "SELECT * FROM plots WHERE farm_id = ? ORDER BY id", (str(farm_id),)
            )
        return [dict(row) for row in rows]


@router.get("/{plot_id}", response_model=Plot)
def get_plot(plot_id: UUID):
    with connect_database() as connection:
        return find_plot(connection, str(plot_id))


@router.patch("/{plot_id}", response_model=Plot)
def update_plot(plot_id: UUID, body: PlotPatch):
    changes = body.model_dump(mode="json", exclude_unset=True)
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        plot = find_plot(connection, str(plot_id))
        plot.update(changes)
        validate_references(connection, plot)
        validate_unique_name(connection, plot)
        if changes:
            assignments = ", ".join(f"{field} = ?" for field in changes)
            connection.execute(
                f"UPDATE plots SET {assignments} WHERE id = ?",
                (*changes.values(), str(plot_id)),
            )
    return plot


@router.delete("/{plot_id}", status_code=204)
def delete_plot(plot_id: UUID) -> Response:
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        find_plot(connection, str(plot_id))
        connection.execute("DELETE FROM plots WHERE id = ?", (str(plot_id),))
    return Response(status_code=204)
