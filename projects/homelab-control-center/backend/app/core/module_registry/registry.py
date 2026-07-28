import json
from pathlib import Path

from app.core.module_registry.schema import Module


REGISTRY_FILE = Path(__file__).parent / "modules.json"


def load_modules() -> list[Module]:
    """
    Load modules from JSON registry
    """

    with open(REGISTRY_FILE, "r") as file:
        data = json.load(file)

    modules = []

    for item in data:
        modules.append(
            Module(
                **item
            )
        )

    return modules


def get_modules() -> list[Module]:
    """
    Return all registered modules
    """

    return load_modules()




def get_module(module_id: str) -> Module | None:
    """
    Find module by id
    """

    modules = load_modules()

    for module in modules:
        if module.module_id == module_id:
            return module

    return None


def save_modules(modules: list[Module]):
    """
    Save module registry to JSON
    """

    with open(REGISTRY_FILE, "w") as file:
        json.dump(
            [m.model_dump() for m in modules],
            file,
            indent=4
        )


def register_module(module: Module):
    """
    Register a new module
    """

    modules = load_modules()

    for existing in modules:
        if existing.module_id == module.module_id:
            raise ValueError(
                f"Module {module.module_id} already exists."
            )

    modules.append(module)

    save_modules(modules)

    return module

