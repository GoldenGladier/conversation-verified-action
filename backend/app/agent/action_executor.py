from datetime import datetime, timedelta

from app.calendar.calendar_tool import CalendarTool
from app.verification.verification_service import (
    VerificationRequest,
    VerificationAction,
)


class ActionExecutor:

    def __init__(self, calendar: CalendarTool):
        self.calendar = calendar

    def execute(
        self,
        request: VerificationRequest
    ) -> str:

        if request.action == VerificationAction.CREATE_CALENDAR_EVENT:
            return self._create_calendar_event(request)

        raise ValueError(
            f"Unsupported verification action: {request.action}"
        )

    def _create_calendar_event(
        self,
        request: VerificationRequest
    ) -> str:

        patient_name = request.payload["patient_name"]
        date = request.payload["date"]
        start_time = request.payload["start_time"]
        duration_minutes = request.payload["duration_minutes"]

        start = datetime.fromisoformat(
            f"{date}T{start_time}"
        )

        end = start + timedelta(
            minutes=duration_minutes
        )

        event = self.calendar.create_event(
            title=f"Cita - {patient_name}",
            start=start,
            end=end
        )

        return (
            f"✅ Cita creada correctamente.\n\n"
            f"Paciente: {patient_name}\n"
            f"Fecha: {date}\n"
            f"Hora: {start_time}\n"
            f"Duración: {duration_minutes} minutos"
        )
