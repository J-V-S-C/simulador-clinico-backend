import json

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from ports.errors import ServiceError

from handlers.api import ApiHandlers, require_token
from routes.schemas import (
    AdvanceRequest, CaseDetail, CaseSummary, HealthResponse, InteractionRequest,
    InteractionResult, LoginRequest, ProtocolResult, RegisterRequest, ReportRequest,
    ReportResponse, ResultResponse, SimulationResponse, SimulationSummary, StartRequest,
    TokenResponse, UserResponse, ErrorResponse, ExperienceFeedback,
)


def create_router(handlers: ApiHandlers) -> APIRouter:
    router = APIRouter(prefix="/api", responses={
        400: {"model": ErrorResponse}, 401: {"model": ErrorResponse},
        404: {"model": ErrorResponse}, 409: {"model": ErrorResponse},
        422: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
    })
    owner = Depends(handlers.owner)
    token = Depends(require_token)

    @router.get("/health", response_model=HealthResponse)
    async def health():
        return handlers.health()

    @router.post("/auth/register", response_model=UserResponse, status_code=201)
    async def register(body: RegisterRequest):
        return handlers.register(body.email, body.password, body.name)

    @router.post("/auth/login", response_model=TokenResponse)
    async def login(body: LoginRequest):
        return handlers.login(body.email, body.password)

    @router.post("/auth/logout", status_code=204)
    async def logout(access_token: str = token, user_id: str = owner):
        handlers.logout(access_token)
        return Response(status_code=204)

    @router.get("/auth/me", response_model=UserResponse)
    async def me(user_id: str = owner):
        return handlers.me(user_id)

    @router.get("/cases", response_model=list[CaseSummary])
    async def cases(user_id: str = owner):
        return handlers.list_cases()

    @router.get("/cases/{case_id}", response_model=CaseDetail)
    async def case(case_id: str, user_id: str = owner):
        return handlers.get_case(case_id)

    @router.post("/simulations", response_model=SimulationResponse, status_code=201)
    async def start(body: StartRequest, user_id: str = owner):
        return handlers.start(user_id, body.case_id, body.time_limit_minutes)

    @router.get("/simulations", response_model=list[SimulationSummary])
    async def list_simulations(limit: int = 20, offset: int = 0, user_id: str = owner):
        return handlers.list_simulations(user_id, limit, offset)

    @router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
    async def get_simulation(simulation_id: str, user_id: str = owner):
        return handlers.get_simulation(user_id, simulation_id)

    @router.post("/simulations/{simulation_id}/interactions", response_model=InteractionResult)
    async def interact(simulation_id: str, body: InteractionRequest, user_id: str = owner):
        return await handlers.interact(user_id, simulation_id, body.student_text, body.symptom_name)

    @router.post("/simulations/{simulation_id}/interactions/stream")
    async def interact_stream(simulation_id: str, body: InteractionRequest, user_id: str = owner):
        async def events():
            try:
                async for kind, value in handlers.interact_stream(user_id, simulation_id, body.student_text, body.symptom_name):
                    yield f"event: {kind}\ndata: {json.dumps(value, ensure_ascii=False)}\n\n"
            except ServiceError as error:
                yield f"event: error\ndata: {json.dumps({'code': error.code, 'message': error.message}, ensure_ascii=False)}\n\n"
            except Exception:
                yield f"event: error\ndata: {json.dumps({'code': 'stream_failed', 'message': 'Não foi possível completar a resposta.'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @router.post("/simulations/{simulation_id}/time/advance", response_model=SimulationResponse)
    async def advance(simulation_id: str, body: AdvanceRequest, user_id: str = owner):
        return handlers.advance(user_id, simulation_id, body.seconds)

    @router.post("/simulations/{simulation_id}/protocols/{symptom_name}/reveal", response_model=ProtocolResult)
    async def reveal(simulation_id: str, symptom_name: str, user_id: str = owner):
        return handlers.reveal(user_id, simulation_id, symptom_name)

    @router.post("/simulations/{simulation_id}/reports", response_model=ReportResponse, status_code=201)
    async def report(simulation_id: str, body: ReportRequest, user_id: str = owner):
        return handlers.report(user_id, simulation_id, body.interaction_id, body.description)

    @router.post("/simulations/{simulation_id}/finish", response_model=SimulationResponse)
    async def finish(simulation_id: str, user_id: str = owner):
        return handlers.finish(user_id, simulation_id)

    @router.get("/simulations/{simulation_id}/result", response_model=ResultResponse)
    async def result(simulation_id: str, user_id: str = owner):
        return handlers.result(user_id, simulation_id)

    @router.get("/simulations/{simulation_id}/experience-feedback", response_model=ExperienceFeedback | None)
    async def get_feedback(simulation_id: str, user_id: str = owner):
        return handlers.feedback(user_id, simulation_id)

    @router.post("/simulations/{simulation_id}/experience-feedback", response_model=ExperienceFeedback, status_code=201)
    async def submit_feedback(simulation_id: str, body: ExperienceFeedback, user_id: str = owner):
        return handlers.submit_feedback(user_id, simulation_id, body.model_dump())

    @router.put("/simulations/{simulation_id}/experience-feedback", response_model=ExperienceFeedback)
    async def update_feedback(simulation_id: str, body: ExperienceFeedback, user_id: str = owner):
        return handlers.update_feedback(user_id, simulation_id, body.model_dump())

    return router
