"""Plot lifecycle endpoints and farm filtering."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import Connection, select

from database import connect_database
from schemas import Plot, PlotCreate, PlotPatch
from tables import crops, emitters, farms, plots, soils


router = APIRouter(prefix="/v1/plots", tags=["plots"])


def find_plot(connection: Connection, plot_id: str, *, lock: bool = False) -> dict:
    query = select(plots).where(plots.c.id == plot_id)
    if lock:
        query = query.with_for_update()
    row = connection.execute(query).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Plot not found.")
    return dict(row)


def validate_references(connection: Connection, plot: dict) -> None:
    for field, table in (
        ("farm_id", farms),
        ("crop_id", crops),
        ("soil_id", soils),
        ("emitter_id", emitters),
    ):
        if connection.execute(
            select(table.c.id).where(table.c.id == plot[field])
        ).first() is None:
            raise HTTPException(status_code=422, detail=f"{field} does not exist.")


def validate_unique_name(connection: Connection, plot: dict) -> None:
    if connection.execute(
        select(plots.c.id).where(
            plots.c.farm_id == plot["farm_id"], plots.c.name == plot["name"], plots.c.id != plot["id"]
        )
    ).first() is not None:
        raise HTTPException(status_code=409, detail="A plot with this name already exists in the farm.")


@router.post("", response_model=Plot, status_code=201)
def create_plot(body: PlotCreate):
    plot = {"id": str(uuid4()), **body.model_dump(mode="json")}
    with connect_database(write=True) as connection:
        validate_references(connection, plot)
        validate_unique_name(connection, plot)
        connection.execute(plots.insert().values(plot))
    return plot


@router.get("", response_model=list[Plot])
def list_plots(farm_id: UUID | None = None):
    query = select(plots).order_by(plots.c.id)
    if farm_id is not None:
        query = query.where(plots.c.farm_id == str(farm_id))
    with connect_database() as connection:
        return [dict(row) for row in connection.execute(query).mappings()]


@router.get("/{plot_id}", response_model=Plot)
def get_plot(plot_id: UUID):
    with connect_database() as connection:
        return find_plot(connection, str(plot_id))


@router.patch("/{plot_id}", response_model=Plot)
def update_plot(plot_id: UUID, body: PlotPatch):
    changes = body.model_dump(mode="json", exclude_unset=True)
    with connect_database(write=True) as connection:
        plot = find_plot(connection, str(plot_id), lock=True)
        plot.update(changes)
        validate_references(connection, plot)
        validate_unique_name(connection, plot)
        if changes:
            connection.execute(plots.update().where(plots.c.id == str(plot_id)).values(changes))
    return plot


@router.delete("/{plot_id}", status_code=204)
def delete_plot(plot_id: UUID) -> Response:
    with connect_database(write=True) as connection:
        find_plot(connection, str(plot_id), lock=True)
        connection.execute(plots.delete().where(plots.c.id == str(plot_id)))
    return Response(status_code=204)
