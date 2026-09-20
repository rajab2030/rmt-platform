"""SQLAlchemy schema contract and append-only audit writes.

PostgreSQL's first-start schema and app-role grants are installed by db/schema.sql.
The app role can only insert into and read the ledger tables; it cannot migrate
the schema, and it can only read (never write) counterparty_reference — risk
tier and sanctions status are owner-managed reference data, not something the
supervisory API can alter about itself.
"""

import os

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import URL

metadata = MetaData()

supervisory_audit_log = Table(
    "supervisory_audit_log",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("timestamp", DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()),
    Column("agent_id", Text, nullable=False),
    Column("channel", Text),
    Column("payload_hash", String(64), nullable=False),
    Column("risk_evaluation_result", JSONB, nullable=False),
    Column("final_decision", Text, nullable=False),
    Column("request_path", Text, nullable=False),
    Column("violation_reason", Text),
    CheckConstraint("final_decision IN ('Authorized', 'Rejected')"),
)

simulated_release_queue = Table(
    "simulated_release_queue",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("audit_id", BigInteger, ForeignKey("supervisory_audit_log.id"), nullable=False, unique=True),
    Column("agent_id", Text, nullable=False),
    Column("transaction_id", Text, nullable=False),
    Column("counterparty_id", Text, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("amount", Numeric(14, 2), nullable=False),
    Column("amount_usd_equivalent", Numeric(14, 2), nullable=False),
    Column("correspondent_bank_id", Text),
    Column("payload_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()),
    UniqueConstraint("agent_id", "transaction_id", name="uq_release_agent_transaction"),
)

counterparty_reference = Table(
    "counterparty_reference",
    metadata,
    Column("counterparty_id", Text, primary_key=True),
    Column("risk_tier", Text, nullable=False),
    Column("sanctioned", Boolean, nullable=False),
    Column("notes", Text),
)

# Correspondent banking relationships. Unlike counterparty_reference (where an
# unregistered beneficiary defaults to MEDIUM tier), an unregistered
# correspondent has no relationship at all and is always treated as
# unapproved — cross-border settlement requires an actual onboarded
# correspondent, not a default.
correspondent_bank_reference = Table(
    "correspondent_bank_reference",
    metadata,
    Column("correspondent_bank_id", Text, primary_key=True),
    Column("approved", Boolean, nullable=False),
    Column("sanctioned", Boolean, nullable=False),
    Column("nostro_exposure_cap", Numeric(14, 2), nullable=False),
    Column("notes", Text),
)

fx_rate_reference = Table(
    "fx_rate_reference",
    metadata,
    Column("currency", String(3), primary_key=True),
    Column("usd_rate", Numeric(18, 8), nullable=False),
)


def make_engine():
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["MCR_DB_USER"],
        password=os.environ["MCR_DB_PASSWORD"],
        host=os.environ["MCR_DB_HOST"],
        database=os.environ["MCR_DB_NAME"],
    )
    return create_engine(url, pool_pre_ping=True)
