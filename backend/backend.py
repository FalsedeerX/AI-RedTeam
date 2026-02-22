import uvicorn
from fastapi import FastAPI
from app.api.routes import UsersRouter, ProjectsRouter


def initialize_server() -> FastAPI:
    app = FastAPI(title="Backend API", version="0.1.0")
    register_routers(app)
    return app


def register_routers(app: FastAPI) -> None:
    app.include_router(UsersRouter().router)
    app.include_router(ProjectsRouter().router)


# create a server instance
app = initialize_server()


if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)
