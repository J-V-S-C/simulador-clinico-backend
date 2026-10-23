from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class CaseSummary(BaseModel):
    id: str
    title: str


class CaseDetail(CaseSummary):
    default_time_limit_minutes: int
    max_time_limit_minutes: int


class StartRequest(BaseModel):
    case_id: str
    time_limit_minutes: int = Field(default=5, ge=1, le=10)


class InteractionRequest(BaseModel):
    student_text: str = Field(min_length=1, max_length=2000)
    symptom_name: str


class AdvanceRequest(BaseModel):
    seconds: int = Field(ge=1, le=600)


class ReportRequest(BaseModel):
    interaction_id: str
    description: str = Field(min_length=1, max_length=2000)


class ExperienceFeedback(BaseModel):
    liked: bool
    clarity: int = Field(ge=1, le=5)
    difficulty: int = Field(ge=1, le=5)
    useful_feature: str = Field(default="", max_length=1000)
    improvement: str = Field(default="", max_length=1000)


class InteractionResponse(BaseModel):
    id: str
    student_text: str
    patient_response: str
    classification: str
    evaluated_symptom_name: str
    input_tokens: int
    output_tokens: int


class VitalSignResponse(BaseModel):
    name: str
    value: float
    unit: str
    is_critical: bool
    baseline_value: float
    critical_value: float | None


class SymptomResponse(BaseModel):
    name: str
    intensity: float
    severity: str
    state: str
    is_complex: bool


class ProtocolState(BaseModel):
    symptom_name: str
    revealed_level: int
    reference_source: str | None
    content: list[str]


class ResultResponse(BaseModel):
    clinical_evolution: str
    time_elapsed: float
    definitive_outcome: str
    feedback: str


class SimulationResponse(BaseModel):
    id: str
    is_running: bool
    disease_name: str | None
    time_limit_minutes: int
    elapsed_time_minutes: int
    remaining_seconds: int = Field(ge=0)
    interactions: list[InteractionResponse]
    protocol_progress: dict[str, int]
    protocols: list[ProtocolState]
    vital_signs: list[VitalSignResponse]
    symptoms: list[SymptomResponse]
    result: ResultResponse | None


class SimulationSummary(BaseModel):
    id: str
    is_running: bool
    elapsed_time_minutes: int
    time_limit_minutes: int


class InteractionResult(BaseModel):
    interaction_id: str
    simulation: SimulationResponse


class ProtocolResult(BaseModel):
    symptom_name: str
    level: int
    content: str
    has_next_level: bool


class ReportResponse(BaseModel):
    id: str
    interaction_id: str
    description: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
