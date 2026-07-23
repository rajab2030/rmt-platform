from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.docker_api import get_containers
from app.schemas.container import Container

app = FastAPI(
    title="RMT Platform Center",
    version="0.1"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.142.128:5173",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "RMT Platform Control Center",
        "version": "0.1"
    }


@app.get("/containers", response_model=list[Container])
def containers():
    return get_containers()

