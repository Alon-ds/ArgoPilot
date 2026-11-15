import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_to_service_sqlite_file(self):
        with patch.dict(os.environ, clear=True):
            url = Settings(_env_file=None).database_url
        self.assertEqual(url.drivername, "sqlite")
        self.assertEqual(Path(url.database).name, "registry.db")
        self.assertEqual(Path(url.database).parent, Path(__file__).resolve().parents[1])

    def test_environment_overrides_dotenv(self):
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text("DATABASE_URL=sqlite:///other.db\n")
            with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/registry"}):
                url = Settings(_env_file=dotenv).database_url
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.database, "registry")

    def test_invalid_url_is_rejected_without_echoing_credentials(self):
        with patch.dict(os.environ, {"DATABASE_URL": "mysql://user:secret@localhost/db"}):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL") as result:
                Settings(_env_file=None)
        self.assertNotIn("secret", str(result.exception))
