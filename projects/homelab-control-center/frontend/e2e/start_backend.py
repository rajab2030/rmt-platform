"""Start an isolated backend for Playwright acceptance tests."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = FRONTEND_DIR.parent / "backend"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rmt-budget-browser-") as data_dir:
        data_path = Path(data_dir)
        os.environ.update(
            {
                "RMT_AUTH_ENABLED": "true",
                "RMT_OPERATOR_TOKENS": (
                    "admin:admin-token,owner:owner-token,"
                    "requester:requester-token,stranger:stranger-token"
                ),
                "RMT_BUDGET_BOOTSTRAP_PRINCIPAL": "admin",
                "RMT_BUDGET_DB": str(data_path / "budget.db"),
                "RMT_EVIDENCE_DB": str(data_path / "governance-evidence.db"),
                "RMT_CORS_ORIGINS": "http://localhost:15173",
                "RMT_API_PORT": "18080",
                "RMT_EVIDENCE_RETENTION_DAYS": "0",
                "RMT_RUNTIME_ENGINE": "simulation",
                "RMT_HOMELAB_LOOP_ENABLED": "false",
            }
        )
        os.chdir(BACKEND_DIR)
        sys.path.insert(0, str(BACKEND_DIR))

        import app.core.intelligence.memory.storage as memory_storage
        import app.core.observability.storage as observability_storage

        isolated_observability = data_path / "observability.db"
        memory_storage.DB_PATH = isolated_observability
        observability_storage.DB_PATH = isolated_observability

        import app.main as main_app

        async def idle_collector():
            await asyncio.Event().wait()

        main_app.collect_metrics = idle_collector

        import uvicorn

        uvicorn.run(
            main_app.app,
            host="127.0.0.1",
            port=18080,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
