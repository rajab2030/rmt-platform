CREATE ROLE mcr_app LOGIN PASSWORD :'app_password';

CREATE TABLE supervisory_audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    agent_id TEXT NOT NULL,
    channel TEXT,
    payload_hash CHAR(64) NOT NULL,
    risk_evaluation_result JSONB NOT NULL,
    final_decision TEXT NOT NULL CHECK (final_decision IN ('Authorized', 'Rejected')),
    request_path TEXT NOT NULL,
    violation_reason TEXT
);

CREATE TABLE simulated_release_queue (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    audit_id BIGINT NOT NULL UNIQUE REFERENCES supervisory_audit_log(id),
    agent_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    counterparty_id TEXT NOT NULL,
    currency CHAR(3) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    amount_usd_equivalent NUMERIC(14, 2) NOT NULL,
    correspondent_bank_id TEXT,
    payload_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_release_agent_transaction UNIQUE (agent_id, transaction_id)
);

CREATE INDEX idx_release_agent_created ON simulated_release_queue (agent_id, created_at);
CREATE INDEX idx_release_agent_counterparty_created ON simulated_release_queue (agent_id, counterparty_id, created_at);
CREATE INDEX idx_release_correspondent_created ON simulated_release_queue (correspondent_bank_id, created_at)
    WHERE correspondent_bank_id IS NOT NULL;

-- Owner-managed reference data. The MCR application role may only SELECT this
-- table: risk tier and sanctions status are policy inputs the supervisor
-- reads, never something it (or a subordinate) can set about itself.
CREATE TABLE counterparty_reference (
    counterparty_id TEXT PRIMARY KEY,
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH')),
    sanctioned BOOLEAN NOT NULL DEFAULT false,
    notes TEXT
);

INSERT INTO counterparty_reference (counterparty_id, risk_tier, sanctioned, notes) VALUES
    ('SANCTIONED-DEMO-01', 'HIGH', true, 'seeded demo sanctions-list entry'),
    ('TRUSTED-DEMO-01', 'LOW', false, 'seeded demo low-risk counterparty'),
    ('HIGHRISK-DEMO-01', 'HIGH', false, 'seeded demo high-risk-tier counterparty');

-- Owner-managed correspondent banking relationships and FX rates. Same
-- SELECT-only contract as counterparty_reference: the MCR reads these, it
-- never writes them.
CREATE TABLE correspondent_bank_reference (
    correspondent_bank_id TEXT PRIMARY KEY,
    approved BOOLEAN NOT NULL DEFAULT false,
    sanctioned BOOLEAN NOT NULL DEFAULT false,
    nostro_exposure_cap NUMERIC(14, 2) NOT NULL,
    notes TEXT
);

INSERT INTO correspondent_bank_reference (correspondent_bank_id, approved, sanctioned, nostro_exposure_cap, notes) VALUES
    ('CORR-APPROVED-01', true, false, 40000.00, 'seeded demo approved correspondent, ample nostro cap'),
    ('CORR-TIGHT-01', true, false, 3000.00, 'seeded demo approved correspondent, tight nostro cap'),
    ('CORR-UNAPPROVED-01', false, false, 0.00, 'seeded demo correspondent with no onboarded relationship'),
    ('CORR-SANCTIONED-01', true, true, 40000.00, 'seeded demo correspondent later added to a sanctions list');

CREATE TABLE fx_rate_reference (
    currency CHAR(3) PRIMARY KEY,
    usd_rate NUMERIC(18, 8) NOT NULL
);

INSERT INTO fx_rate_reference (currency, usd_rate) VALUES
    ('EUR', 1.08000000),
    ('GBP', 1.27000000),
    ('JPY', 0.00670000),
    ('CAD', 0.74000000);

CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'supervisory_audit_log is append-only';
END;
$$;

CREATE TRIGGER supervisory_audit_append_only
BEFORE UPDATE OR DELETE OR TRUNCATE ON supervisory_audit_log
FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation();

REVOKE ALL ON supervisory_audit_log, simulated_release_queue, counterparty_reference,
    correspondent_bank_reference, fx_rate_reference FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mcr_app;
GRANT SELECT, INSERT ON supervisory_audit_log, simulated_release_queue TO mcr_app;
GRANT SELECT ON counterparty_reference, correspondent_bank_reference, fx_rate_reference TO mcr_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mcr_app;
