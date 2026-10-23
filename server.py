"""FastAPI composition root. Run with `uvicorn server:app` from backend/."""

from contextlib import asynccontextmanager


from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from config import BACKEND_DIR, Settings
from handlers.api import ApiHandlers
from integrations.gemini import GeminiEvaluator
from ports.clock import SystemClock
from repositories.database import create_session_factory, run_migrations
from repositories.store import SqlStore, import_legacy_csv, seed_public_cases
from routes.api import create_router
from services.auth import AuthService
from services.cases import CaseService
from ports.errors import ServiceError
from services.reports import ReportService
from services.simulations import SimulationService


def create_app(settings: Settings | None = None, evaluator=None, clock=None, store=None) -> FastAPI:
    settings = settings or Settings()
    if store is None:
        run_migrations(settings.database_url)
        factory = create_session_factory(settings.database_url, create_schema=False)
        import_legacy_csv(factory, BACKEND_DIR / "data")
        seed_public_cases(factory)
        store = SqlStore(factory)
    clock = clock or SystemClock()
    evaluator = evaluator or GeminiEvaluator(settings.api_key, settings.gemini_model, settings.gemini_timeout_seconds)
    handlers = ApiHandlers(
        AuthService(store, clock), CaseService(store),
        SimulationService(store, evaluator, clock), ReportService(store),
    )
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            if isinstance(evaluator, GeminiEvaluator):
                await evaluator.aclose()

    app = FastAPI(
        title="Simulador Clínico API",
        version="1.0.0",
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "defaultModelExpandDepth": 0,
        },
    )

    @app.get("/", include_in_schema=False)
    async def documentation():
        return RedirectResponse(url="/docs")

    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(ServiceError)
    async def service_error(_request: Request, error: ServiceError):
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": "Dados da requisição inválidos."}})

    app.include_router(create_router(handlers))
    return app


app = create_app()
