"""RMT-CAP-02 curated engineering metadata (above-Core).

This is an EXPLICITLY CURATED, thin map of engineering metadata for known
components. It is NOT a complete repository model, NOT an AST scanner, and
NOT a knowledge graph. It exists only to give the read-only analysis a
deterministic, human-curated link between a component and its source/tests.

Entries are curated by hand and must be kept accurate; they are engineering
metadata, not authoritative architecture.
"""
CURATED_ENGINEERING_METADATA = {
    "control-center": {
        "source_files": [
            "app/main.py",
            "app/core/platform_state/service.py",
        ],
        "test_files": [
            "app/core/platform_state/testing/test_platform_state_provider.py",
        ],
        "notes": "Platform management console; governed execution entrypoint.",
    },
    "uptime-kuma": {
        "source_files": [
            "app/homelab/remediation.py",
            "app/homelab/observer.py",
            "app/homelab/verification.py",
        ],
        "test_files": [
            "app/homelab/testing/test_integrated.py",
            "app/homelab/testing/test_remediation.py",
            "app/homelab/testing/test_observer.py",
        ],
        "notes": "Monitoring service; governed remediation target (CAP-01).",
    },
    "portainer": {
        "source_files": [],
        "test_files": [],
        "notes": "Management UI (context-registry entry; no curated source map).",
    },
    "dozzle": {
        "source_files": [],
        "test_files": [],
        "notes": "Logging service (context-registry entry; no curated source map).",
    },
}


def get_curated_metadata(component: str):
    """Return curated engineering metadata for a component, or None."""
    return CURATED_ENGINEERING_METADATA.get(component)
