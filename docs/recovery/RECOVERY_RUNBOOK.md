# HomeLab Disaster Recovery Runbook

## Purpose

This document defines the tested procedure to recover the HomeLab platform after a failure.

The objective is to restore services with verified data integrity and confirmed service availability.

## Scope

This runbook covers the **Docker stack** (volumes, compose config, images). It
does **not** cover:

- The **RMT governance evidence** (authorization / approval / audit / trace /
  verification stores + `observability.db`) → `docs/operations/RMT_EVIDENCE_RECOVERY.md`
  (RMT-PROD **E5**: `rmt-evidence-backup.sh` / `rmt_evidence_verify.py` /
  `rmt-evidence-restore.sh`).
- The **RMT service** itself (venv, systemd unit, drop-ins) →
  `docs/operations/DEPLOY.md`; a full bare-host rebuild is **R3** (open).

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
