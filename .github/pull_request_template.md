## What and why

## How it was validated

- [ ] `scripts/ci.sh --fast` passes (backend changes)
- [ ] `npm run lint` and `npm run build` pass (frontend changes)

## Checklist

- [ ] No changes under `backend/app/core/**`
- [ ] Nothing that mutates state bypasses the governed path
- [ ] Docs and stated limits updated if behaviour changed
- [ ] No secrets, personal data or host-specific paths
