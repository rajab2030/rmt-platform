# Contributing to RMT

Thanks for looking. The most useful contributions right now:

- **Setup reports.** Did the [quickstart](quickstart/README.md) work on your
  machine (especially Windows/WSL or macOS), and how long did it take? Post in
  [Discussions](https://github.com/rajab2030/rmt-platform/discussions).
- **Actions RMT can't represent.** A consequential action you'd want governed
  that doesn't fit the lifecycle is a valuable issue, even without a fix.
- **Issues labelled
  [`good first issue`](https://github.com/rajab2030/rmt-platform/labels/good%20first%20issue).**

## Ground rules

- **Don't modify `projects/homelab-control-center/backend/app/core/**`.** The
  Core is frozen and validated by its own test suite. If a change seems to
  need Core to behave differently, open an issue describing the gap instead;
  a Core change needs an explicit, written decision from the maintainer. See
  [`docs/RMT_FROZEN_CORE_DEBT.md`](docs/RMT_FROZEN_CORE_DEBT.md).
- **Nothing that mutates state may bypass the governed path.** Execution
  adapters execute; they never authorize, approve, or create governance
  evidence.
- **Keep guarantees honest.** Docs and messages state what is and isn't
  guaranteed. Don't strengthen a claim without evidence.
- **Small, single-purpose changes.** One change, one responsibility, one test
  that proves it.
- **No secrets, personal data, or host-specific paths** in code, docs, logs or
  screenshots.

Working with an AI coding agent? Point it at [`AGENTS.md`](AGENTS.md), the
operating contract agents follow in this repository.

## Development setup

Backend (Python 3.12), from `projects/homelab-control-center/backend`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/uvicorn app.main:app --reload
```

Frontend (Node), from `projects/homelab-control-center/frontend`:

```bash
npm install
npm run dev
```

## Before you open a pull request

Run the same gate CI runs, from `projects/homelab-control-center/backend`:

```bash
scripts/ci.sh --fast   # reuses .venv: ruff (errors only), import smoke, full test suite
```

The full suite takes several minutes because it waits in real time on approval
holds and loop cadence. Please don't mock those waits to speed it up; the
timing behaviour is what's under test. To run the gate automatically before
every push:

```bash
git config core.hooksPath .githooks
```

For frontend changes, also run `npm run lint` and `npm run build`.

## Pull requests

- Describe what changed, why, and how you validated it.
- Add or update tests for behaviour changes.
- Update docs when behaviour or limits change.
- By contributing you agree your work is licensed under the
  [MIT License](LICENSE).

## Security issues

Please don't open public issues for vulnerabilities; see
[`SECURITY.md`](SECURITY.md).
