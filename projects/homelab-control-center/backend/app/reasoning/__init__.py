"""RMT-CAP-13 -- Evidence-Grounded Incident Explainer (above-Core).

An LLM *explains* an incident from evidence RMT already holds; every claim must
cite a record from the evidence bundle it was shown, or it is dropped. Slice 1
is read-only: no import path to the governed mutation path or any adapter, and
the only write target is this package's own ``reasoning.db``.

See ``docs/RMT_CAP_13_PROPOSAL.md``.
"""
