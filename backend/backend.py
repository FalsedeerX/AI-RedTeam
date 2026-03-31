import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import UsersRouter, ProjectsRouter, TargetsRouter, ScansRouter, ReportsRouter, AgentRouter


def initialize_server() -> FastAPI:
    app = FastAPI(title="AI RedTeam API", version="0.1.0")
    _register_middleware(app)
    _register_routers(app)
    return app


def _register_middleware(app: FastAPI) -> None:
    # Allow the Vite dev server (default port 5173) to reach the API.
    # Extend origins as needed for production deployment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_routers(app: FastAPI) -> None:
    app.include_router(UsersRouter().router)
    app.include_router(ProjectsRouter().router)
    app.include_router(TargetsRouter().router)
    app.include_router(ScansRouter().router)
    app.include_router(ReportsRouter().router)
    app.include_router(AgentRouter().router)


# Keep the old name for any code that still calls register_routers directly.
register_routers = _register_routers


# create a server instance
app = initialize_server()


if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)
