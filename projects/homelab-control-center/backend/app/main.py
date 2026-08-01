from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.docker_api import (
    get_containers,
    get_container_stats,
    start_container,
    stop_container,
    restart_container,
    create_container,
    remove_container,

)
from app.schemas.container import Container

from app.monitor import get_history
from app.collector import collect_metrics

from app.core.module_registry.registry import get_modules
from app.core.configuration.settings import load_settings

from app.core.configuration.public import create_public_config
from app.core.platform_state.service import get_platform_state

from app.core.observability.api import router as observability_router
import asyncio


collector_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global collector_task

    collector_task = asyncio.create_task(
        collect_metrics()
    )

    yield

    if collector_task:
        collector_task.cancel()


app = FastAPI(
    title="RMT Platform Center",
    version="0.1",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.235.128:5173",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(observability_router)

@app.get("/")
def root():
    return {
        "name": "RMT Platform Control Center",
        "version": "0.1"
    }


@app.get("/containers", response_model=list[Container])
def containers():
    return get_containers()

@app.get("/modules")
def modules():
    return get_modules()

@app.get("/config")
def config():

    settings = load_settings()

    return create_public_config(
        settings
    )

@app.get("/platform/state")
def platform_state():
    return get_platform_state()

@app.get("/containers/{name}/stats")
def container_stats(name: str):
    return get_container_stats(name)


@app.get("/monitor/history")
def history():
    return get_history()


@app.post("/containers/{name}/start")
def start(name: str):
    return start_container(name)


@app.post("/containers/{name}/stop")
def stop(name: str):
    return stop_container(name)


@app.post("/containers/{name}/restart")
def restart(name: str):
    return restart_container(name)


@app.post("/containers/create")
def create(
    name: str,
    image: str
):
    return create_container(
        name,
        image
    )

@app.delete("/containers/{name}")
def remove(name: str):
    return remove_container(name)


