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


def get_container_stats(name):
    container = client.containers.get(name)

    stats = container.stats(stream=False)

    return {
        "name": container.name,
        "status": container.status,
        "memory_usage": stats["memory_stats"].get("usage", 0),
    }
