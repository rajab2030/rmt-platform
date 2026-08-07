from datetime import datetime, timezone, timedelta


class FakeMetric:

    def __init__(
        self,
        name,
        status="running",
        health="healthy",
        cpu_usage=10,
        memory_usage=20,
        age_seconds=0,
    ):

        self.name = name

        self.status = status

        self.health = health

        self.cpu_usage = cpu_usage

        self.memory_usage = memory_usage

        self.timestamp = (
            datetime.now(timezone.utc)
            -
            timedelta(seconds=age_seconds)
        )


def healthy_container():

    return FakeMetric(
        name="test-service",
        status="running",
        cpu_usage=20,
        memory_usage=30,
    )


def stopped_container():

    return FakeMetric(
        name="test-service",
        status="stopped",
        health="unhealthy",
    )


def stale_container():

    return FakeMetric(
        name="test-service",
        age_seconds=3600,
    )



def no_metric():

    return None





