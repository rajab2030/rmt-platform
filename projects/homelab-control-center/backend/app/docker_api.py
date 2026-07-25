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

    memory_usage = stats.get(
        "memory_stats", {}
    ).get(
        "usage",
        0
    )


    cpu_percent = 0.0

    cpu_stats = stats.get(
        "cpu_stats",
        {}
    )

    precpu_stats = stats.get(
        "precpu_stats",
        {}
    )


    cpu_usage = cpu_stats.get(
        "cpu_usage",
        {}
    )

    precpu_usage = precpu_stats.get(
        "cpu_usage",
        {}
    )


    cpu_delta = (
        cpu_usage.get("total_usage", 0)
        -
        precpu_usage.get("total_usage", 0)
    )


    system_delta = (
        cpu_stats.get("system_cpu_usage", 0)
        -
        precpu_stats.get("system_cpu_usage", 0)
    )


    if system_delta > 0 and cpu_delta > 0:
        cpu_percent = (
            cpu_delta
            /
            system_delta
        ) * len(
            cpu_usage.get(
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

def start_container(name: str):
    container = client.containers.get(name)
    container.start()

    return {
        "name": name,
        "action": "start",
        "status": "success"
    }


def stop_container(name: str):
    container = client.containers.get(name)
    container.stop()

    return {
        "name": name,
        "action": "stop",
        "status": "success"
    }


def restart_container(name: str):
    container = client.containers.get(name)
    container.restart()

    return {
        "name": name,
        "action": "restart",
        "status": "success"
    }


def create_container(
    name: str,
    image: str
):
    container = client.containers.run(
        image,
        name=name,
        detach=True
    )

    return {
        "name": container.name,
        "image": image,
        "status": "created"
    }


def remove_container(name: str):
    container = client.containers.get(name)

    container.remove(
        force=True
    )

    return {
        "name": name,
        "action": "remove",
        "status": "success"
    }

