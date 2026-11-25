"""Create and seed an EMPTY configured database without deleting existing data."""
from pathlib import Path
from sqlalchemy import text
from config import settings
from database import database_engine


def seed():
    source = Path(__file__).with_name("seed_registry.sh").read_text()
    sql = source.split("<<'SQL'\n", 1)[1].split("\nSQL", 1)[0]
    with database_engine(settings.database_url).begin() as connection:
        for statement in sql.split(";"):
            if statement.strip() and not statement.strip().startswith("PRAGMA"):
                connection.execute(text(statement))
    print("Seeded 16 rows: 2 farms, 4 plots, 3 crops, 3 soils, 4 emitters")


if __name__ == "__main__":
    seed()
