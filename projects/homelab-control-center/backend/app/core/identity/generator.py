import uuid
import re


def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def generate_module_id(name: str) -> str:
    slug = slugify(name)
    short_id = uuid.uuid4().hex[:6]

    return f"{slug}-{short_id}"
