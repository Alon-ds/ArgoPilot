"""Exercise the Registry contract against PostgreSQL in disposable schemas."""

import asyncio
import os
import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url

import test_api
from bootstrap import initialize_database
from database import create_registry_engine


@unittest.skipUnless(os.getenv("POSTGRES_TEST_DATABASE_URL"), "PostgreSQL test URL is unset")
class PostgresRegistryTests(test_api.RegistryTests):
    def make_test_engine(self):
        url = make_url(os.environ["POSTGRES_TEST_DATABASE_URL"])
        schema = f"test_{uuid4().hex}"
        admin = create_registry_engine(url)
        self.addCleanup(admin.dispose)
        with admin.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))

        def drop_schema():
            with admin.begin() as connection:
                connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))

        self.addCleanup(drop_schema)
        engine = create_registry_engine(url.update_query_dict({"options": f"-csearch_path={schema}"}))
        self.addCleanup(engine.dispose)
        initialize_database(engine)
        return engine

    async def test_unavailable_database(self):
        url = self.engine.url.set(database=f"missing_{uuid4().hex}")
        self.engine = create_registry_engine(url)
        self.addCleanup(self.engine.dispose)
        response = await self.request("GET", "/v1/farms")
        self.assert_problem(response, 503, "UNAVAILABLE")
        self.assertEqual(response[1][b"retry-after"], b"5")

    @unittest.skip("SQLite file corruption is specific to SQLite")
    async def test_corrupt_database(self):
        pass

    async def test_bootstrap_row_counts_and_repeat_safety(self):
        counts = {"farms": 2, "plots": 4, "crops": 2, "soils": 3, "emitters": 4}
        with self.assertRaisesRegex(ValueError, "empty"):
            initialize_database(self.engine)
        for resource, expected in counts.items():
            status, _, rows = await self.request("GET", f"/v1/{resource}")
            self.assertEqual((status, len(rows)), (200, expected))

    async def test_concurrent_duplicate_plot_is_a_conflict(self):
        responses = await asyncio.gather(
            self.request("POST", "/v1/plots", self.payload),
            self.request("POST", "/v1/plots", self.payload),
        )
        self.assertEqual(sorted(response[0] for response in responses), [201, 409])
        failed = next(response for response in responses if response[0] == 409)
        self.assert_problem(failed, 409, "CONFLICT")
        _, _, plots = await self.request("GET", f"/v1/plots?farm_id={self.payload['farm_id']}")
        self.assertEqual(sum(plot["name"] == self.payload["name"] for plot in plots), 1)
