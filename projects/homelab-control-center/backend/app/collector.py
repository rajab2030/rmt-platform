import asyncio

from app.docker_api import get_container_stats
from app.monitor import save_metric


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
                save_metric(stats)

            except Exception as e:
                print(
                    f"Collector error for {name}: {e}"
                )

        await asyncio.sleep(60)
