import asyncio
from datetime import datetime

from app.docker_api import get_container_stats
from app.monitor import save_metric

from app.core.observability.schemas import ContainerMetric
from app.core.observability.service import record_container_metric


async def collect_metrics():

    while True:

        containers = [
            "portainer",
            "dozzle",
            "uptime-kuma",
        ]

        for name in containers:

            try:

                stats = get_container_stats(name)


                metric = ContainerMetric(
                    name=stats["name"],
                    status=stats["status"],
                    cpu_usage=stats.get("cpu_usage"),
                    memory_usage=stats.get("memory_usage"),
                    health=stats.get("health"),
                    timestamp=datetime.utcnow()
                )


                record_container_metric(metric)


                # compatibility with old monitoring endpoint
                save_metric(stats)


            except Exception as e:

                print(
                    f"Collector error for {name}: {e}"
                )


        await asyncio.sleep(60)
