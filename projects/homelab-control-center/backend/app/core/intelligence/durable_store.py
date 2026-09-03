import json
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

    def _load(self) -> List[BaseModel]:
        if not self._file_path.exists():
            return []
        with open(self._file_path, "r") as f:
            data = json.load(f)
        return [self._model.model_validate(item) for item in data]

    def _persist(self) -> None:
        if not self._file_path:
            return
        with open(self._file_path, "w") as f:
            json.dump(
                [r.model_dump(mode="json") for r in self._records],
                f,
                indent=4,
            )

    def save(self, record: BaseModel) -> None:
        self._records.append(record)
        self._persist()

    def get_all(self) -> List[BaseModel]:
        return self._records
