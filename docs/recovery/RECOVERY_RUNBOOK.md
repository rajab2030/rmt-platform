# Homelab-Domain Disaster Recovery Runbook

## Purpose

This document defines the tested procedure to recover the homelab domain's
Docker stack (RMT Platform's original proving-ground domain) after a
failure. It does not cover the RMT Platform itself — see Scope below.

The objective is to restore services with verified data integrity and confirmed service availability.

## Scope

This runbook covers the **Docker stack** (volumes, compose config, images). It
does **not** cover:

- The **RMT governance evidence** (authorization / approval / audit / trace /
  verification stores + `observability.db`) → `docs/operations/RMT_EVIDENCE_RECOVERY.md`
  (RMT-PROD **E5**: `rmt-evidence-backup.sh` / `rmt_evidence_verify.py` /
  `rmt-evidence-restore.sh`).
- The **RMT service** itself (venv, systemd unit, drop-ins) → routine
  redeploy / rollback: `docs/operations/DEPLOY.md`; a full bare-host rebuild
  (RMT-PROD **R3**): `docs/operations/RMT_PLATFORM_RECOVERY.md` +
  `backend/scripts/rmt-rebuild.sh`.

---

## Recovery Point Location

Recovery points are created by the unified backup engine and stored in:

~/homelab/backups/daily/

Example recovery point:

~/homelab/backups/daily/2026-07-20_09-22

A recovery point contains:

- Docker stack configuration
- Docker metadata
- Documentation
- Scripts
- Docker volume backups
- Manifest
- SHA256 checksums

---

# Recovery Procedure

## Step 1 — Select Recovery Point

List available backups:

```bash
ls -lt ~/homelab/backups/daily
