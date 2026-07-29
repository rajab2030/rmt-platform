from pathlib import Path
import yaml
import os

from app.core.configuration.schema import Settings


CONFIG_FILE = (
    Path(__file__).parents[3]
    / "config"
    / "config.yaml"
)


def load_settings() -> Settings:

    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    # Environment overrides

    if os.getenv("RMT_ENV"):
        data["environment"]["name"] = os.getenv("RMT_ENV")

    if os.getenv("RMT_DEBUG"):
        data["environment"]["debug"] = (
            os.getenv("RMT_DEBUG").lower() == "true"
        )

    if os.getenv("RMT_API_HOST"):
        data["api"]["host"] = os.getenv("RMT_API_HOST")

    if os.getenv("RMT_API_PORT"):
        data["api"]["port"] = int(
            os.getenv("RMT_API_PORT")
        )

    if os.getenv("RMT_RUNTIME_ENGINE"):
        data["runtime"]["engine"] = os.getenv(
            "RMT_RUNTIME_ENGINE"
        )

    return Settings(**data)
