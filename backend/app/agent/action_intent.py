from datetime import date as Date, time as Time

from pydantic import BaseModel

from app.verification.verification_service import (
    VerificationAction,
)


class ActionIntent(BaseModel):
    action: VerificationAction | None = None
    patient_name: str | None = None
    date: Date | None = None
    start_time: Time | None = None
    duration_minutes: int | None = None