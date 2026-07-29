from pathlib import Path
import yaml

from app.core.configuration.schema import Settings


CONFIG_FILE = (
    Path(__file__).parents[3]
    / "config"
    / "config.yaml"
)


def load_settings() -> Settings:

    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    return Settings(**data)
