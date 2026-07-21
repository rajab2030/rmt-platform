from fastapi import FastAPI
from app.docker_api import get_containers


app = FastAPI(
    title="HomeLab Control Center",
    version="0.1"
)


@app.get("/")
def root():
    return {
        "name": "HomeLab Control Center",
        "version": "0.1"
    }


@app.get("/containers")
def containers():
    return get_containers()
