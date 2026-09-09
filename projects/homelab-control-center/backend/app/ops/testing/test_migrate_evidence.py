"""T0-1 -- rmt-migrate-evidence.py: JSON -> SQLite -> --reverse round-trips
byte-for-byte, and forward migration is idempotent / --force overwrites.
"""
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts" / "rmt-migrate-evidence.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("_migrate", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sample(tmp_path):
    """A temp app/core/intelligence-shaped tree with two populated stores,
    written through the same model_dump(mode="json") path the live JSON stores
    use -- so a byte-for-byte round-trip is a real assertion, not an artefact
    of a hand-written fixture."""
    from app.core.intelligence.actions.approval import ApprovalRecord
    from app.core.intelligence.verification.models import VerificationResult

    base = tmp_path / "ci"
    (base / "actions").mkdir(parents=True)
    (base / "verification").mkdir(parents=True)
    (base / "execution").mkdir(parents=True)

    records = [
        ApprovalRecord(approval_id="p1", action_id="a1",
                       decision="approved", approved_by="ops"),
        ApprovalRecord(approval_id="p2", action_id="a2",
                       decision="rejected", approved_by="ops", reason="no"),
    ]
    verifs = [
        VerificationResult(verification_id="v1", execution_id="e1",
                           status="verified_success", reason="ok"),
    ]

    def _dump(path, items):
        path.write_text(
            json.dumps([i.model_dump(mode="json") for i in items], indent=4)
        )

    ar = base / "actions" / "approval_records.json"
    vr = base / "verification" / "verifications.json"
    _dump(ar, records)
    _dump(vr, verifs)
    return base, {"approval_records": ar, "verifications": vr}


def test_forward_then_reverse_round_trips_byte_for_byte(sample, tmp_path):
    base, files = sample
    before = {k: p.read_text() for k, p in files.items()}
    db = tmp_path / "governance_evidence.db"
    mig = _load_script()

    assert mig.forward(db, force=False, base=base) == 2
    # forward renames the sources
    for p in files.values():
        assert not p.exists()
        assert p.with_suffix(".json.migrated").exists()

    assert mig.reverse(db, base=base) == 2
    after = {k: p.read_text() for k, p in files.items()}
    assert after == before


def test_forward_is_idempotent_and_force_overwrites(sample, tmp_path):
    base, files = sample
    db = tmp_path / "governance_evidence.db"
    mig = _load_script()

    assert mig.forward(db, force=False, base=base) == 2
    # sources are gone; a second run finds nothing and touches nothing
    assert mig.forward(db, force=False, base=base) == 0

    # restore a source and prove --force clears + re-migrates just that table
    files["verifications"].write_text(
        files["verifications"].with_suffix(".json.migrated").read_text()
    )
    assert mig.forward(db, force=True, base=base) == 1

    from app.core.intelligence.verification.storage import VerificationStorage
    assert len(VerificationStorage(file_path=db).get_all()) == 1
