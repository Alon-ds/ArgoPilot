"""Portable definitions of the P1 Registry tables."""

from sqlalchemy import Column, Double, ForeignKey, Integer, MetaData, Table, Text, UniqueConstraint


metadata = MetaData(naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"})

farms = Table("farms", metadata, Column("id", Text, primary_key=True), Column("name", Text, nullable=False))
crops = Table("crops", metadata, Column("id", Text, primary_key=True), Column("name", Text, nullable=False))
soils = Table(
    "soils", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("available_water_mm_per_m", Integer, nullable=False),
)
emitters = Table(
    "emitters", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("flow_lph", Double, nullable=False),
)
plots = Table(
    "plots", metadata,
    Column("id", Text, primary_key=True),
    Column("farm_id", Text, ForeignKey("farms.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("area_m2", Double, nullable=False),
    Column("crop_id", Text, ForeignKey("crops.id"), nullable=False),
    Column("planting_date", Text, nullable=False),
    Column("soil_id", Text, ForeignKey("soils.id"), nullable=False),
    Column("row_spacing_m", Double, nullable=False),
    Column("emitter_spacing_m", Double, nullable=False),
    Column("emitter_id", Text, ForeignKey("emitters.id"), nullable=False),
    Column("lat", Double, nullable=False),
    Column("lon", Double, nullable=False),
    UniqueConstraint("farm_id", "name", name="uq_plots_farm_id_name"),
)
