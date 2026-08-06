from app.core.intelligence.context.registry import (
    get_component_context,
)


def enrich_component(metric):

    context = get_component_context(
        metric.name
    )

    return {
        "metric": metric,
        "context": context,
    }
