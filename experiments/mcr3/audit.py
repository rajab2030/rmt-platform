"""
Static Boundary Audit (Experiment #3)
======================================
Inspects the implementation for any consequential mutation path that could
bypass the MCR-controlled mutation boundary. This is a manual/static audit
complementing the adversarial campaign.

It looks for: direct state writes, setters, mutable references, aliases,
helper functions, alternate mutation primitives, adapters, caches, object
exposure, serialization/deserialization, init/setup functions, hidden state,
background operations, callbacks, exception/recovery paths.
"""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List

HERE = os.path.dirname(__file__)


def read_src(name: str) -> str:
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def audit() -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    sim = read_src("sim_world.py")
    tools = read_src("tools.py")
    mcr = read_src("mcr.py")

    # 1. Direct writes to protected state outside the sanctioned path.
    #    Look for `.write(` calls and where they occur.
    for fname, src in [("sim_world.py", sim), ("tools.py", tools)]:
        for m in re.finditer(r"\.write\(", src):
            line = src[:m.start()].count("\n") + 1
            findings.append({
                "category": "state_write", "file": fname, "line": line,
                "detail": "call to ProtectedState.write()",
            })

    # 2. Direct attribute writes to _data / _token (bypass primitives).
    for fname, src in [("sim_world.py", sim), ("tools.py", tools)]:
        for m in re.finditer(r"\._data\b|\._token\b", src):
            line = src[:m.start()].count("\n") + 1
            findings.append({
                "category": "private_attr_access", "file": fname, "line": line,
                "detail": m.group(0),
            })

    # 3. Setters / mutators defined on World.
    for m in re.finditer(r"def (set_\w+|_apply\w*|mutate|_preview)\(", sim):
        findings.append({
            "category": "mutator", "file": "sim_world.py",
            "line": sim[:m.start()].count("\n") + 1, "detail": m.group(1),
        })

    # 4. All World methods that could mutate.
    tree = ast.parse(sim)
    world_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "World":
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    world_methods.append(item.name)
    findings.append({"category": "world_methods", "detail": sorted(world_methods)})

    # 5. Tool handlers that call world.mutate vs anything else.
    tree = ast.parse(tools)
    mutate_calls = 0
    other_world_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "mutate":
                mutate_calls += 1
            elif node.func.attr in ("_apply", "_apply_resource", "_apply_flag",
                                    "_services", "_resources", "_flags", "_token"):
                other_world_calls.append(node.func.attr)
    findings.append({
        "category": "tool_mutation_routing",
        "world_mutate_calls_in_tools": mutate_calls,
        "direct_private_calls_in_tools": sorted(set(other_world_calls)),
    })

    # 6. Serialization / deserialization paths.
    for fname, src in [("sim_world.py", sim), ("tools.py", tools)]:
        for m in re.finditer(r"json\.(dumps|loads)|pickle|deepcopy", src):
            findings.append({
                "category": "serialization", "file": fname,
                "line": src[:m.start()].count("\n") + 1, "detail": m.group(0),
            })

    # 7. Background operations / callbacks / threads.
    for fname, src in [("sim_world.py", sim), ("tools.py", tools)]:
        for m in re.finditer(r"thread|Thread|asyncio|schedule|callback|signal|atexit", src):
            findings.append({
                "category": "background/callback", "file": fname,
                "line": src[:m.start()].count("\n") + 1, "detail": m.group(0),
            })

    # 8. Exception/recovery paths that might write state.
    for m in re.finditer(r"except\s|finally|PermissionError", sim):
        findings.append({
            "category": "exception_path", "file": "sim_world.py",
            "line": sim[:m.start()].count("\n") + 1, "detail": m.group(0),
        })

    # 9. Fixture/setup writes (set_service, set_resource, set_flag).
    fixture_writes = []
    for m in re.finditer(r"def (set_service|set_resource|set_flag)\(", sim):
        fixture_writes.append(m.group(1))
    findings.append({"category": "fixture_setup_writes", "detail": fixture_writes})

    return {"findings": findings}


if __name__ == "__main__":
    result = audit()
    with open(os.path.join(HERE, "evidence", "static_audit.json"), "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(json.dumps(result, indent=2, sort_keys=True))
