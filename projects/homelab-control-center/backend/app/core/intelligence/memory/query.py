from app.core.intelligence.memory.service import (
    get_history,
)


def get_component_history(component: str):

    return get_history(
        component
    )


def get_recent_events(
    component: str,
    event_type: str | None = None,
    limit: int = 10,
):

    history = get_history(
        component
    )


    if event_type:

        history = [
            item
            for item in history
            if item.event_type == event_type
        ]


    return sorted(
        history,
        key=lambda item: item.timestamp,
        reverse=True,
    )[:limit]


def get_health_history(component: str):

    return get_recent_events(
        component,
        event_type="health_evaluation",
    )


def get_previous_failures(component: str):

    history = get_health_history(
        component
    )


    return [
        item
        for item in history
        if item.data.get("status")
        in [
            "warning",
            "critical",
        ]
    ]
