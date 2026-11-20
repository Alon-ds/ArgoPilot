"""Optional live PostgreSQL contract test (enabled in CI and local validation)."""
import asyncio
import os
from unittest.mock import patch

import pytest
import database
import test_api


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="needs isolated seeded PostgreSQL")
def test_postgres_contract():
    async def check():
        request = test_api.RegistryTests().request
        for table, count in (("farms", 2), ("plots", 4), ("crops", 2), ("soils", 3), ("emitters", 4)):
            status, _, rows = await request("GET", f"/v1/{table}")
            assert status == 200 and len(rows) == count
            status, _, row = await request("GET", f"/v1/{table}/{rows[0]['id']}")
            assert status == 200 and row == rows[0]
        status, _, farm = await request("POST", "/v1/farms", {"name": "P2 isolated verification"})
        assert status == 201
        try:
            status, _, updated = await request("PATCH", f"/v1/farms/{farm['id']}", {"name": "Updated"})
            assert status == 200 and updated["name"] == "Updated"
        finally:
            status, _, _ = await request("DELETE", f"/v1/farms/{farm['id']}")
            assert status == 204
    with patch.object(database.settings, "database_url", os.environ["TEST_POSTGRES_URL"]):
        asyncio.run(check())
