"""T0-1 follow-up -- rmt_evidence_verify.py understands governance_evidence.db.

The E5 verifier must pass a good T0-1 evidence db, fail a missing/corrupt table,
and keep cross-store advisories non-fatal -- in both the backup layout
(``<dir>/governance_evidence.db``) and the live layout
(``<backend>/data/governance_evidence.db``).
"""
import importlib.util
import sqlite3
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "rmt_evidence_verify.py"
)


def _verify():
    spec = importlib.util.spec_from_file_location("_verify", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_db(path, *, orphan_authz=False):
    from app.core.intelligence.verification.storage import VerificationStorage
    from app.core.intelligence.verification.models import VerificationResult
    from app.core.intelligence.actions.approval_storage import (
        ApprovalHoldStorage,
        ApprovalRecordStorage,
    )
    from app.core.intelligence.actions.approval import ApprovalRecord
    from app.core.intelligence.actions.authorization_storage import (
        AuthorizationStorage,
    )
    from app.core.intelligence.actions.authorization import (
        ExecutionAuthorization,
        AuthorizationStatus,
    )
    from app.core.intelligence.execution.trace_storage import (
        ExecutionTraceStorage,
    )
    from app.core.intelligence.execution.storage import ExecutionAuditStorage

    # instantiate all six so every table exists, as it does in a real db
    for cls in (ApprovalHoldStorage, ExecutionTraceStorage,
                ExecutionAuditStorage):
        cls(file_path=path)

    VerificationStorage(file_path=path).save(
        VerificationResult(execution_id="e1", status="verified_success")
    )
    ApprovalRecordStorage(file_path=path).save(
        ApprovalRecord(approval_id="p1", action_id="a1",
                       decision="approved", approved_by="ops")
    )
    AuthorizationStorage(file_path=path).save(
        ExecutionAuthorization(
            authorization_id="z1", action_id="a1",
            approval_id="p9" if orphan_authz else "p1",
            status=AuthorizationStatus.APPROVED,
            target="web", operation="restart",
        )
    )


def test_good_backup_layout_db_passes(tmp_path, capsys):
    _make_db(tmp_path / "governance_evidence.db")
    rc = _verify().main(["x", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RESULT: OK" in out
    assert "approval_records" in out and "1 row(s)" in out


def test_good_live_layout_db_passes(tmp_path):
    (tmp_path / "data").mkdir()
    _make_db(tmp_path / "data" / "governance_evidence.db")
    assert _verify().main(["x", str(tmp_path)]) == 0


def test_missing_table_is_fatal(tmp_path, capsys):
    db = tmp_path / "governance_evidence.db"
    _make_db(db)
    con = sqlite3.connect(db)
    con.execute("DROP TABLE traces")
    con.commit()
    con.close()

    rc = _verify().main(["x", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing table 'traces'" in out
    assert "RESULT: FAIL" in out


def test_orphan_authorization_is_advisory_not_fatal(tmp_path, capsys):
    _make_db(tmp_path / "governance_evidence.db", orphan_authz=True)
    rc = _verify().main(["x", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no approval record" in out
    assert "RESULT: OK" in out


def test_no_evidence_at_all_is_fatal(tmp_path):
    (tmp_path / "stores").mkdir()  # backup-shaped but empty
    assert _verify().main(["x", str(tmp_path)]) == 1
