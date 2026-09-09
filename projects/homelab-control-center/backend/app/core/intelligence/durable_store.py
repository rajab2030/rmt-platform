import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Type

from pydantic import BaseModel


# Shared SQLite database for the governance-evidence stores (T0-1). Overridable
# via RMT_EVIDENCE_DB (tests point it at a throwaway file); the default lives
# under the already-git-ignored data/ dir, matching
# app/core/observability/storage.py.
EVIDENCE_DB_PATH = Path(
    os.environ.get("RMT_EVIDENCE_DB", "data/governance_evidence.db")
)


class DurableStore:
    """
    Record store behind a stable interface, with three interchangeable backends
    chosen by the path handed to ``__init__``:

      * ``file_path is None``  -> in-memory only (isolated test instances).
      * ``file_path`` ``.json`` -> JSON file. The whole list is rewritten on every
        mutation via an atomic ``.tmp`` + ``fsync`` + ``os.replace``
        (production-readiness item E1). Retained for the one-shot migration and
        its ``--reverse``.
      * ``file_path`` ``.db``   -> a table (``_table``) in a shared SQLite
        database. ``save()`` is a single O(1) ``INSERT``; the file does not grow
        by rewrite; updates and the retention trim are per-row; crash-atomic via
        WAL (T0-1, owner-authorised Option A -- persistence mechanism only, no
        API / record-shape / behaviour change).

    In every backend an in-memory list ``self._records`` mirrors the store and is
    what ``get_all()`` and the subclass ``get_by_*`` lookups read, so those are
    unchanged. Pydantic v2 ``model_dump(mode="json")`` / ``model_validate`` handle
    datetime, enum, and nested models. The stored record shape is identical
    across backends: the SQLite ``payload`` column holds exactly the JSON object
    the JSON backend writes.
    """

    # Subclasses set these for the SQLite backend.
    _table: Optional[str] = None
    _key_field: Optional[str] = None

    def __init__(
        self,
        file_path: Optional[Path] = None,
        model: Optional[Type[BaseModel]] = None,
    ):
        self._file_path = Path(file_path) if file_path is not None else None
        self._model = model
        self._lock = threading.Lock()
        self._sqlite = (
            self._file_path is not None
            and self._file_path.suffix == ".db"
        )
        self._conn: Optional[sqlite3.Connection] = None
        if self._sqlite:
            self._conn = self._open_sqlite()
        self._records: List[BaseModel] = (
            self._load() if self._file_path is not None else []
        )

    # --- SQLite backend (T0-1) ------------------------------------------------

    def _open_sqlite(self) -> sqlite3.Connection:
        if not self._table:
            raise ValueError(
                f"{type(self).__name__} has no _table set for the SQLite "
                "backend"
            )
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._file_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(
            f'CREATE TABLE IF NOT EXISTS "{self._table}" ('
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "key TEXT, "
            "created_at TEXT, "
            "payload TEXT NOT NULL)"
        )
        conn.execute(
            f'CREATE INDEX IF NOT EXISTS "{self._table}_key_idx" '
            f'ON "{self._table}"(key)'
        )
        conn.execute(
            f'CREATE INDEX IF NOT EXISTS "{self._table}_created_at_idx" '
            f'ON "{self._table}"(created_at)'
        )
        conn.commit()
        return conn

    def _key_of(self, record: BaseModel):
        if not self._key_field:
            return None
        return getattr(record, self._key_field, None)

    def _created_at_of(self, record: BaseModel):
        v = getattr(record, "created_at", None)
        if v is None:
            return None
        return v.isoformat() if hasattr(v, "isoformat") else str(v)

    def _row(self, record: BaseModel):
        return (
            self._key_of(record),
            self._created_at_of(record),
            json.dumps(record.model_dump(mode="json")),
        )

    def _sql_insert(self, record: BaseModel) -> None:
        with self._conn:
            self._conn.execute(
                f'INSERT INTO "{self._table}" (key, created_at, payload) '
                "VALUES (?, ?, ?)",
                self._row(record),
            )

    def _sql_replace_all(self, records: List[BaseModel]) -> None:
        with self._conn:
            self._conn.execute(f'DELETE FROM "{self._table}"')
            self._conn.executemany(
                f'INSERT INTO "{self._table}" (key, created_at, payload) '
                "VALUES (?, ?, ?)",
                [self._row(r) for r in records],
            )

    def _sql_update_by_key(self, key, record: BaseModel) -> None:
        with self._conn:
            self._conn.execute(
                f'UPDATE "{self._table}" SET key = ?, created_at = ?, '
                "payload = ? WHERE key = ?",
                (*self._row(record), key),
            )

    def _sql_load(self) -> List[BaseModel]:
        rows = self._conn.execute(
            f'SELECT payload FROM "{self._table}" ORDER BY id'
        ).fetchall()
        return [
            self._model.model_validate(json.loads(r[0])) for r in rows
        ]

    # --- JSON backend (E1) --------------------------------------------------

    def _tmp_path(self) -> Path:
        return self._file_path.with_name(self._file_path.name + ".tmp")

    def _load_json(self) -> List[BaseModel]:
        # Residue from an interrupted write: the committed file (if any) is
        # authoritative, so discard the partial .tmp.
        tmp_path = self._tmp_path()
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        if not self._file_path.exists():
            return []
        with open(self._file_path, "r") as f:
            data = json.load(f)
        return [self._model.model_validate(item) for item in data]

    def _persist(self) -> None:
        # JSON backend only: whole-file atomic rewrite. The SQLite backend
        # writes per row in save() / _commit_update() / _replace_records() and
        # never routes through here.
        if self._file_path is None or self._sqlite:
            return
        tmp_path = self._tmp_path()
        with open(tmp_path, "w") as f:
            json.dump(
                [r.model_dump(mode="json") for r in self._records],
                f,
                indent=4,
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self._file_path)

    # --- common ----------------------------------------------------------

    def _load(self) -> List[BaseModel]:
        return self._sql_load() if self._sqlite else self._load_json()

    def _archive_path(self) -> Optional[Path]:
        """Companion append-only archive file for E4 retention. One per store:
        the SQLite backend keys it by table name (all six share one .db)."""
        if self._file_path is None:
            return None
        if self._sqlite:
            return self._file_path.with_name(
                f"{self._table}.archive.jsonl"
            )
        return self._file_path.with_name(
            self._file_path.stem + ".archive.jsonl"
        )

    def _commit_update(self, index: int, new_record: BaseModel) -> None:
        """Replace the record at ``index`` in place and persist just that change
        (SQLite: one UPDATE; JSON: atomic whole-file rewrite)."""
        with self._lock:
            old_key = self._key_of(self._records[index])
            self._records[index] = new_record
            if self._sqlite:
                self._sql_update_by_key(old_key, new_record)
            else:
                self._persist()

    def _replace_records(self, records: List[BaseModel]) -> None:
        """Replace the entire store contents. Used by E4 retention after it has
        written the aged records to the archive. Backend-aware."""
        with self._lock:
            self._records = list(records)
            if self._sqlite:
                self._sql_replace_all(self._records)
            else:
                self._persist()

    def save(self, record: BaseModel) -> None:
        with self._lock:
            self._records.append(record)
            if self._sqlite:
                self._sql_insert(record)
            else:
                self._persist()

    def get_all(self) -> List[BaseModel]:
        return self._records
