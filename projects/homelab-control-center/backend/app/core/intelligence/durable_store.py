import json
import os
from pathlib import Path
from typing import List, Optional, Type

from pydantic import BaseModel


class DurableStore:
    """
    Minimal JSON-file-backed store.

    Loads existing records on init and persists on each save. Uses Pydantic
    v2 model_dump(mode="json") / model_validate so datetime, enum, and nested
    models serialize/deserialize correctly.

    When file_path is None the store is in-memory only (used for isolated
    test instances); the module-level singletons pass a real file path.

    Persistence is atomic (write a sibling ``.tmp`` file, fsync, then
    ``os.replace``): a reader never observes a partially written file and an
    interrupted write leaves the previous good file intact. The committed file
    contents are byte-for-byte identical to a direct write. (Authorized
    production-readiness hardening, item E1 -- no API, format, or behaviour
    change for any caller.)
    """

    def __init__(
        self,
        file_path: Optional[Path] = None,
        model: Optional[Type[BaseModel]] = None,
    ):
        self._file_path = file_path
        self._model = model
        self._records: List[BaseModel] = (
            self._load() if file_path else []
        )

    def _tmp_path(self) -> Path:
        return self._file_path.with_name(self._file_path.name + ".tmp")

    def _load(self) -> List[BaseModel]:
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
        if not self._file_path:
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

    def save(self, record: BaseModel) -> None:
        self._records.append(record)
        self._persist()

    def get_all(self) -> List[BaseModel]:
        return self._records
