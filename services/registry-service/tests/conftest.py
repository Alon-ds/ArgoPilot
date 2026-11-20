"""Release pooled connections before temporary test directories are removed."""
import pytest
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///registry.db")
import database


@pytest.fixture(autouse=True)
def close_database_pools():
    created = []
    original = database.create_engine

    def track(*args, **kwargs):
        engine = original(*args, **kwargs)
        created.append(engine)
        return engine

    database.database_engine.cache_clear()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(database, "create_engine", track)
        yield
    for engine in created:
        engine.dispose()
    database.database_engine.cache_clear()
