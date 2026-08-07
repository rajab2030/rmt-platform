from app.core.intelligence.testing.observation_fixtures import (
    healthy_observation,
)

from app.core.intelligence.testing.fixtures import (
    healthy_container,
)

from app.core.intelligence.observation.service import (
    observe_container,
)


def run():
    print("=== fake observation ===")
    print(
        healthy_observation().model_dump()
    )

    print("\n=== docker adapter observation ===")

    print(
        observe_container(
            healthy_container()
        ).model_dump()
    )


if __name__ == "__main__":
    run()
