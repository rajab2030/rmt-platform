from app.core.intelligence.testing.fixtures import (
    stopped_container,
    stale_container,
)

from app.core.intelligence.testing.observation_fixtures import (
    healthy_observation,
)

from app.core.intelligence.observation.normalize import (
    normalize_observation,
)

from app.core.intelligence.rules import (
    create_health_evaluation,
    evaluate_observation_health,
)


def test_metric_normalizes_to_observation():

    observation = normalize_observation(
        stopped_container()
    )

    assert observation.component == "test-service"
    assert observation.state == "stopped"


def test_observation_health_evaluation():

    observation = healthy_observation()

    result = evaluate_observation_health(
        observation
    )

    assert result["status"].value == "healthy"


def test_create_health_evaluation_from_metric():

    result = create_health_evaluation(
        stopped_container()
    )

    assert result.reason.value == "collector_failure"


def test_stale_observation_detection():

    result = create_health_evaluation(
        stale_container()
    )

    assert result.reason.value == "stale_data"
