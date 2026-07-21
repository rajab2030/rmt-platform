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
