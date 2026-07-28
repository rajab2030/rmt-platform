from app.core.identity.generator import generate_module_id

from app.core.module_registry.schema import (
    Module,
    RuntimeInfo,
    HealthInfo
)


def create_module(
    name: str,
    version: str,
    module_type: str,
    runtime_engine: str = "docker",
    container: str | None = None,
):

    module_id = generate_module_id(name)

    return Module(
        module_id=module_id,
        name=name,
        version=version,
        type=module_type,
        status="active",

        runtime=RuntimeInfo(
            engine=runtime_engine,
            container=container
        ),

        health=HealthInfo(
            status="unknown"
        )
    )
