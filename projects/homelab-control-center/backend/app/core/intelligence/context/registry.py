from app.core.intelligence.context.models import ComponentContext


COMPONENT_CONTEXTS = {

    "portainer": ComponentContext(
        name="portainer",
        role="management",
        criticality="medium",
        dependencies=[],
    ),

    "uptime-kuma": ComponentContext(
        name="uptime-kuma",
        role="monitoring",
        criticality="high",
        dependencies=[],
    ),

    "dozzle": ComponentContext(
        name="dozzle",
        role="logging",
        criticality="medium",
        dependencies=[],
    ),
}


def get_component_context(name: str):

    return COMPONENT_CONTEXTS.get(name)
