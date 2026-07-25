import docker


client = docker.from_env()


def get_containers():
    containers = client.containers.list(all=True)

    result = []

    for container in containers:
        result.append(
            {
                "name": container.name,
                "image": container.image.tags[0]
                if container.image.tags
                else "unknown",
                "status": container.status,
            }
        )

    return result


def get_container_stats(name: str):
    container = client.containers.get(name)

    stats = container.stats(stream=False)

    memory_usage = stats["memory_stats"].get("usage", 0)


    cpu_delta = (
        stats["cpu_stats"]["cpu_usage"]["total_usage"]
        -
        stats["precpu_stats"]["cpu_usage"]["total_usage"]
    )


    system_delta = (
        stats["cpu_stats"]["system_cpu_usage"]
        -
        stats["precpu_stats"]["system_cpu_usage"]
    )


    cpu_percent = 0.0

    if system_delta > 0 and cpu_delta > 0:
        cpu_percent = (
            cpu_delta
            /
            system_delta
        ) * len(
            stats["cpu_stats"]["cpu_usage"].get(
                "percpu_usage",
                [1]
            )
        ) * 100
    health_status = (
        container.attrs["State"]
        .get("Health", {})
        .get("Status", "none")
    )



    return {
        "name": container.name,
        "status": container.status,
        "memory_usage": memory_usage,
        "cpu_usage": round(cpu_percent, 2),
        "started_at": container.attrs["State"]["StartedAt"],
        "health": health_status,
    }

