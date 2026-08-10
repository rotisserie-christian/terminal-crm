import logging
import sqlite3
from pathlib import Path
from src.utils.exceptions import CrmDbError

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/crm.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    website TEXT,
    trade TEXT,
    signals TEXT,
    hiring TEXT,
    phone TEXT,
    is_hiring INTEGER NOT NULL DEFAULT 0,
    has_ads INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_phone
ON leads(phone)
WHERE phone IS NOT NULL AND phone != '';

CREATE TABLE IF NOT EXISTS call_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
"""


class CrmDatabase:
    """
    Manages the local SQLite CRM database

    Responsibilities:
    - Ensure the data directory exists
    - Open connections to the DB file
    - Create tables/indexes if missing
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize CRM database storage

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_data_directory()
        self._initialize_schema()

    def _ensure_data_directory(self) -> None:
        """
        Create the database parent directory if it does not exist

        Raises:
            CrmDbError: If the directory cannot be created
        """
        data_dir = self.db_path.parent
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied creating {data_dir}")
            raise CrmDbError(
                f"Cannot create data directory: Permission denied"
            ) from e
        except OSError as e:
            logger.error(f"Failed to create data directory: {e}", exc_info=True)
            raise CrmDbError(f"Cannot create data directory: {e}") from e

    def connect(self) -> sqlite3.Connection:
        """
        Open a connection to the CRM database

        Returns:
            sqlite3.Connection with row_factory set to sqlite3.Row

        Raises:
            CrmDbError: If the database cannot be opened
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to open CRM database: {e}", exc_info=True)
            raise CrmDbError(f"Cannot open CRM database: {e}") from e

    def _initialize_schema(self) -> None:
        """
        Create CRM tables and indexes if they do not exist

        Raises:
            CrmDbError: If schema initialization fails
        """
        try:
            with self.connect() as conn:
                conn.executescript(SCHEMA_SQL)
            logger.info(f"CRM schema ready at {self.db_path}")
        except CrmDbError:
            raise
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize CRM schema: {e}", exc_info=True)
            raise CrmDbError(f"Cannot initialize CRM schema: {e}") from e

    def table_names(self) -> list[str]:
        """
        List user tables in the database

        Returns:
            Sorted list of table names
        """
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]
