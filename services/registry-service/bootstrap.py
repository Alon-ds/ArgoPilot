"""Create Registry tables and load the P1 seed data into an empty database."""

from pathlib import Path

from sqlalchemy import Engine, select

from database import create_registry_engine
from config import Settings
from tables import metadata


def initialize_database(engine: Engine) -> None:
    seed_sql = Path(__file__).with_name("seed_data.sql").read_text(encoding="utf-8")
    with engine.connect() as connection:
        connection.execution_options(registry_write=True)
        with connection.begin():
            metadata.create_all(connection)
            for table in metadata.sorted_tables:
                if connection.execute(select(table.c.id).limit(1)).first() is not None:
                    raise ValueError("Registry seed data requires an empty database.")
            for statement in seed_sql.split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement)


def main() -> None:
    engine = create_registry_engine(Settings().database_url, create=True)
    try:
        initialize_database(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
