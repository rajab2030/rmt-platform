from app.core.intelligence.context.registry import (
    get_component_context,
)


def enrich_component(observation):

    context = get_component_context(
        observation.component
    )

    return {
        "observation": observation,
        "context": context,
    }
