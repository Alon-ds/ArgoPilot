"""API integration tests using isolated SQLite databases and in-process ASGI."""

import json
import shutil
import sqlite3
import unittest
from contextlib import ExitStack, closing
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from database import connect_database, create_registry_engine
from sqlalchemy import text
from sqlalchemy.exc import ResourceClosedError
from main import app


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.engine = self.make_test_engine()
        self.addCleanup(self.engine.dispose)
        self.stack.enter_context(patch("database.get_engine", lambda: self.engine))
        with connect_database() as connection:
            self.sample = dict(connection.execute(text("SELECT * FROM plots LIMIT 1")).mappings().one())
            self.other_farm = connection.execute(
                text("SELECT id FROM farms WHERE id != :id"), {"id": self.sample["farm_id"]}
            ).scalars().first()
        self.payload = {key: value for key, value in self.sample.items() if key != "id"}
        self.payload["name"] = "New plot"

    def make_test_engine(self):
        directory = self.stack.enter_context(TemporaryDirectory())
        self.database = Path(directory) / "test.db"
        service = Path(__file__).resolve().parents[1]
        seed = (service / "seed_registry.sh").read_text()
        ddl = seed.split("<<'SQL'\n", 1)[1].split("\nSQL", 1)[0]
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript(ddl + "\n" + (service / "seed_data.sql").read_text() + "\nCOMMIT;")
        return create_registry_engine(f"sqlite:///{self.database}")

    async def request(self, method, url, payload=None, raw=None):
        url = urlsplit(url)
        messages = []
        body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b""

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app(
            {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": url.path,
                "raw_path": url.path.encode(), "query_string": url.query.encode(),
                "root_path": "", "headers": [(b"content-type", b"application/json")],
                "server": ("test", 80), "client": ("test", 1),
            }, receive, send,
        )
        content = b"".join(message.get("body", b"") for message in messages[1:])
        return messages[0]["status"], dict(messages[0]["headers"]), json.loads(content) if content else None

    def assert_problem(self, response, status, code):
        actual_status, headers, body = response
        self.assertEqual(actual_status, status)
        self.assertEqual(headers[b"content-type"], b"application/problem+json")
        self.assertEqual(body["status"], status)
        self.assertEqual(body["code"], code)
        for field in ("type", "title", "detail", "instance"):
            self.assertIsInstance(body[field], str)

    async def test_health_and_missing_route(self):
        status, _, body = await self.request("GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))
        self.assert_problem(await self.request("GET", "/missing"), 404, "NOT_FOUND")

    async def test_catalogs_and_rejected_writes(self):
        for table, count in (("crops", 2), ("soils", 3), ("emitters", 4)):
            with self.subTest(table=table):
                status, _, items = await self.request("GET", f"/v1/{table}")
                self.assertEqual(status, 200)
                self.assertEqual(len(items), count)
                for item in items:
                    status, _, body = await self.request("GET", f"/v1/{table}/{item['id']}")
                    self.assertEqual((status, body), (200, item))
                for missing in ("missing", "' OR 1=1 --"):
                    self.assert_problem(await self.request("GET", f"/v1/{table}/{missing}"), 404, "NOT_FOUND")
                for path in (f"/v1/{table}", f"/v1/{table}/{items[0]['id']}"):
                    for method in ("POST", "PUT", "PATCH", "DELETE"):
                        response = await self.request(method, path, {})
                        self.assert_problem(response, 405, "METHOD_NOT_ALLOWED")
                        self.assertIn(b"GET", response[1][b"allow"])

    async def test_farm_lifecycle_and_persistence(self):
        status, _, farm = await self.request("POST", "/v1/farms", {"name": " New farm "})
        self.assertEqual(status, 201)
        UUID(farm["id"])
        self.assertEqual(farm["name"], "New farm")
        path = f"/v1/farms/{farm['id']}"
        self.assertEqual((await self.request("GET", path))[2], farm)
        status, _, updated = await self.request("PATCH", path, {"name": "Updated"})
        self.assertEqual((status, updated), (200, {**farm, "name": "Updated"}))
        self.assertEqual((await self.request("PATCH", path, {}))[2], updated)
        with connect_database() as connection:
            self.assertEqual(connection.execute(text("SELECT name FROM farms WHERE id = :id"), {"id": farm["id"]}).scalar_one(), "Updated")
        self.assertEqual((await self.request("DELETE", path)), (204, {}, None))
        for method in ("GET", "PATCH", "DELETE"):
            self.assert_problem(await self.request(method, path, {} if method == "PATCH" else None), 404, "NOT_FOUND")

    async def test_farm_validation_and_delete_conflict(self):
        path = f"/v1/farms/{self.sample['farm_id']}"
        before = (await self.request("GET", path))[2]
        for body in ({}, {"name": ""}, {"name": " "}, {"name": None}, {"name": "x", "extra": 1}):
            self.assert_problem(await self.request("POST", "/v1/farms", body), 422, "VALIDATION")
            if body:
                self.assert_problem(await self.request("PATCH", path, body), 422, "VALIDATION")
        self.assert_problem(await self.request("DELETE", path), 409, "CONFLICT")
        self.assertEqual((await self.request("GET", path))[2], before)

    async def test_plot_lifecycle_partial_update_and_persistence(self):
        status, _, plot = await self.request("POST", "/v1/plots", self.payload)
        self.assertEqual(status, 201)
        UUID(plot["id"])
        path = f"/v1/plots/{plot['id']}"
        self.assertEqual((await self.request("GET", path))[2], plot)
        status, _, updated = await self.request("PATCH", path, {"area_m2": 2222})
        self.assertEqual((status, updated), (200, {**plot, "area_m2": 2222}))
        self.assertEqual((await self.request("PATCH", path, {}))[2], updated)
        with connect_database() as connection:
            self.assertEqual(connection.execute(text("SELECT area_m2 FROM plots WHERE id = :id"), {"id": plot["id"]}).scalar_one(), 2222)
        self.assertEqual(await self.request("DELETE", path), (204, {}, None))
        for method in ("GET", "PATCH", "DELETE"):
            self.assert_problem(await self.request(method, path, {} if method == "PATCH" else None), 404, "NOT_FOUND")

    async def test_plot_validation_leaves_existing_data_unchanged(self):
        path = f"/v1/plots/{self.sample['id']}"
        invalid = [{"name": " "}, {"planting_date": "invalid"},
                   {"planting_date": (date.today() + timedelta(days=1)).isoformat()},
                   {"farm_id": str(uuid4())}, {"farm_id": "invalid"}, {"unexpected": 1}]
        for field in ("area_m2", "row_spacing_m", "emitter_spacing_m"):
            invalid.extend({field: value} for value in (0, -1, "NaN", "Infinity"))
        for field, limit in (("lat", 90), ("lon", 180)):
            invalid.extend({field: value} for value in (limit + 1, -limit - 1))
        invalid.extend({field: "missing"} for field in ("crop_id", "soil_id", "emitter_id"))
        invalid.extend({field: None} for field in self.payload)
        for change in invalid:
            with self.subTest(change=change):
                self.assert_problem(await self.request("POST", "/v1/plots", {**self.payload, **change}), 422, "VALIDATION")
                self.assert_problem(await self.request("PATCH", path, change), 422, "VALIDATION")
                self.assertEqual((await self.request("GET", path))[2], self.sample)

    async def test_plot_uniqueness_and_farm_transfer(self):
        status, _, plot = await self.request("POST", "/v1/plots", self.payload)
        self.assertEqual(status, 201)
        path = f"/v1/plots/{plot['id']}"
        self.assert_problem(await self.request("POST", "/v1/plots", self.payload), 409, "CONFLICT")
        self.assert_problem(await self.request("PATCH", path, {"name": self.sample["name"]}), 409, "CONFLICT")
        status, _, _ = await self.request("POST", "/v1/plots", {**self.payload, "farm_id": self.other_farm})
        self.assertEqual(status, 201)
        self.assert_problem(await self.request("PATCH", path, {"farm_id": self.other_farm}), 409, "CONFLICT")
        self.assertEqual((await self.request("GET", path))[2], plot)
        status, _, moved = await self.request("PATCH", path, {"farm_id": self.other_farm, "name": "Moved"})
        self.assertEqual(status, 200)
        self.assertEqual(moved["farm_id"], self.other_farm)

    async def test_filtering_empty_lists_and_uuid_validation(self):
        status, _, items = await self.request("GET", f"/v1/plots?farm_id={self.sample['farm_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["farm_id"] == self.sample["farm_id"] for item in items))
        self.assertEqual((await self.request("GET", f"/v1/plots?farm_id={uuid4()}"))[2], [])
        for path in ("/v1/plots?farm_id=bad", "/v1/plots/bad", "/v1/farms/bad"):
            self.assert_problem(await self.request("GET", path), 422, "VALIDATION")
        with connect_database() as connection:
            connection.execute(text("DELETE FROM plots"))
            connection.execute(text("DELETE FROM farms"))
        for table in ("plots", "farms"):
            status, _, items = await self.request("GET", f"/v1/{table}")
            self.assertEqual((status, items), (200, []))

    async def test_malformed_json(self):
        self.assert_problem(await self.request("POST", "/v1/farms", raw=b'{"name":'), 422, "VALIDATION")

    async def test_unavailable_database(self):
        self.database = self.database.parent / "missing.db"
        self.engine.dispose()
        self.engine = create_registry_engine(f"sqlite:///{self.database}")
        for path in ("/v1/farms", "/v1/plots", "/v1/crops", "/v1/soils", "/v1/emitters"):
            response = await self.request("GET", path)
            self.assert_problem(response, 503, "UNAVAILABLE")
            self.assertEqual(response[1][b"retry-after"], b"5")
            self.assertNotIn(str(self.database), response[2]["detail"])
        self.assertFalse(self.database.exists())

    async def test_corrupt_database(self):
        self.engine.dispose()
        self.database.write_bytes(b"This is not a SQLite database.")
        for path in ("/v1/farms", "/v1/plots", "/v1/crops"):
            response = await self.request("GET", path)
            self.assert_problem(response, 503, "UNAVAILABLE")
            self.assertEqual(response[1][b"retry-after"], b"5")

    async def test_sqlite_replacement_is_visible_to_next_request(self):
        if self.engine.dialect.name != "sqlite":
            self.skipTest("SQLite file replacement is specific to SQLite")
        farm_id = self.sample["farm_id"]
        path = f"/v1/farms/{farm_id}"
        self.assertEqual((await self.request("GET", path))[0], 200)
        replacement = self.database.with_name("replacement.db")
        shutil.copyfile(self.database, replacement)
        with closing(sqlite3.connect(replacement)) as connection, connection:
            connection.execute("UPDATE farms SET name = ? WHERE id = ?", ("Restored", farm_id))
        replacement.replace(self.database)
        self.assertEqual((await self.request("GET", path))[2]["name"], "Restored")

    async def test_connection_rollback_close_and_foreign_keys(self):
        with self.assertRaises(RuntimeError):
            with connect_database() as connection:
                if connection.dialect.name == "sqlite":
                    self.assertEqual(connection.execute(text("PRAGMA foreign_keys")).scalar_one(), 1)
                connection.execute(text("INSERT INTO farms VALUES (:id, :name)"), {"id": str(uuid4()), "name": "Rollback"})
                raise RuntimeError("abort transaction")
        with self.assertRaises(ResourceClosedError):
            connection.execute(text("SELECT 1"))
        with connect_database() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM farms")).fetchone()[0], 2)
            if connection.dialect.name == "sqlite":
                self.assertEqual(connection.execute(text("PRAGMA foreign_key_check")).fetchall(), [])


if __name__ == "__main__":
    unittest.main()
